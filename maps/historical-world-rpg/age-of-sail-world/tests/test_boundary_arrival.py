import copy
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from boundary_arrival import endpoint, resolve, ARRIVAL_TOLERANCE
from materialize_physical_map import materialize
from package_wurst_map import generate, load_config
from package_wurst_campaign import load_campaign_config, validate_campaign, _inspect_physical_map, PackagingError
from warcraft_campaign import write_mpq, MpqReader


class BoundaryNavigationTests(unittest.TestCase):
    def test_blocked_land_snaps_nearest_within_tolerance_not_to_disconnected_island(self):
        width = height = 32
        cells = [1] * (width*height)
        # A disconnected patch is closer to the ideal than connected land.
        for y in range(11, 22):
            for x in range(1, 5):
                cells[y*width+x] = 0
        cells[16*width+2] = 1
        e = endpoint(width, height, cells, (0, 0, width, height), 'west', (0, 1))
        self.assertIsNone(resolve(e, .5))
        self.assertIsNone(resolve(e, float('nan')))
        self.assertIsNone(resolve(e, float('inf')))
        # A short obstruction allows a bounded move, still in the edge component.
        cells = [1] * (width*height)
        cells[16*width+1] = 0
        e = endpoint(width, height, cells, (0, 0, width, height), 'west', (0, 1))
        x, y = resolve(e, .5)
        self.assertEqual((-1856., -32.), (x, y))
        self.assertLessEqual((x+2048)**2+y*y, ARRIVAL_TOLERANCE**2)

    def test_water_requires_connection_to_entry_and_correct_movement(self):
        cells = [2] * 1024
        for y in range(10, 23):
            for x in range(1, 5):
                cells[y*32+x] = 3  # decorative water, blocked in WPM
        cells[16*32+2] = 2  # pathable but isolated water
        e = endpoint(32, 32, cells, (0, 0, 32, 32), 'west', (0, 1))
        self.assertIsNone(resolve(e, .5, movement=1))
        self.assertIsNone(resolve(e, .5, movement=0))
        cells = [2] * 1024
        e = endpoint(32, 32, cells, (0, 0, 32, 32), 'west', (0, 1))
        self.assertEqual((-1856., 0.), resolve(e, .5, movement=1))
        self.assertIsNone(resolve(e, .5, movement=0))

    def test_live_pathing_blocks_ideal_and_can_exhaust_all_candidates(self):
        e = endpoint(32, 32, [1]*1024, (0, 0, 32, 32), 'west', (.2, .8))
        self.assertEqual((-1856., 64.), resolve(e, .5, pathable=lambda x, y, m: y >= 64))
        self.assertIsNone(resolve(e, .5, pathable=lambda x, y, m: False))

    def test_partial_interval_unequal_dimensions_and_return_coordinate(self):
        e = endpoint(64, 32, [1]*2048, (0, 0, 64, 32), 'east', (.2, .6))
        self.assertAlmostEqual(-622.592, resolve(e, .37)[1])
        # reverse -> scale -> offset is the committed coordinate; resolve only
        # interpolates it on the destination segment.
        saved = (1-.37)*.5+.1
        x, y = resolve(e, saved)
        self.assertEqual(3904., x)
        self.assertAlmostEqual(-548.864, y)
        local = ((y+2048)/4096-.2)/.4
        self.assertAlmostEqual(saved, local)


class GeneratedBoundaryArrivalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.generated = cls.root / 'generated'
        cls.config = load_config(PROJECT / 'package.json')
        cls.campaign = load_campaign_config(PROJECT / 'physical-maps.json')
        cls.world = validate_campaign(cls.campaign)
        generate(cls.config, cls.generated)
        cls.runtime = json.loads((cls.generated / 'scenario-runtime.json').read_text())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_generated_destination_edge_is_resolved_from_unique_reverse_record(self):
        records = {b.id: b for b in self.campaign.boundaries}
        nav = self.runtime['boundaryNavigation']
        source = records['middle_east_india_to_europe_central_east']
        reverse = next(b for b in records.values() if b.source_map_id == source.destination_map_id and b.destination_map_id == source.source_map_id)
        e = nav[reverse.id]
        self.assertEqual('east', e['edge'])
        self.assertEqual([(7232., -3968.), (7232., -2186.24), (7232., -256.)],
                         [resolve(e, p) for p in (.25, .37, .5)])
        partial = nav['middle_east_india_to_africa']
        self.assertEqual([.5, 1.], partial['interval'])
        self.assertAlmostEqual(2490.88, resolve(partial, .37)[1])

    def test_generated_coordinates_match_packaged_pathing_and_tampering_is_rejected(self):
        for physical in self.campaign.maps:
            if physical.bootstrap:
                continue
            with self.subTest(map=physical.id):
                map_dir = self.root / physical.id
                map_dir.mkdir()
                shutil.copy2(physical.source_map / 'war3map.w3i', map_dir / 'war3map.w3i')
                runtime = copy.deepcopy(self.runtime)
                runtime['settlementDefinitions'] = [s for s in self.world['settlements'] if s.get('regionalInstanceId') in physical.regional_instance_ids]
                materialize(PROJECT, map_dir, self.generated, physical, runtime)
                (map_dir / 'runtime/scenario-runtime.json').write_text(json.dumps(runtime))
                archive = self.root / f'{physical.id}.w3x'
                files = {p.relative_to(map_dir).as_posix(): p.read_bytes() for p in map_dir.rglob('*') if p.is_file()}
                write_mpq(archive, files)
                _inspect_physical_map(physical, archive)
                reader = MpqReader(archive)
                wpm = reader.read('war3map.wpm')
                pw, ph = struct.unpack_from('<II', wpm, 8)
                for e in runtime['boundaryNavigation'].values():
                    if e['mapId'] != physical.id:
                        continue
                    for movement, mask in ((0, 0x02), (1, 0x40)):
                        for position in (.1, .25, .37, .5, .75, .9):
                            point = resolve(e, position, movement)
                            if point is None:
                                continue
                            x, y = point
                            px, py = int(x/32 + pw/2), int(y/32 + ph/2)
                            self.assertFalse(wpm[16+py*pw+px] & mask)
                            min_x, min_y, max_x, max_y = e['bounds']
                            self.assertTrue(min_x+128 < x < max_x-128)
                            self.assertTrue(min_y+128 < y < max_y-128)
                broken = bytearray(wpm)
                broken[16 + (ph//2)*pw + pw//2] ^= 0x02
                files['war3map.wpm'] = bytes(broken)
                write_mpq(archive, files)
                with self.assertRaisesRegex(PackagingError, 'boundary navigation'):
                    _inspect_physical_map(physical, archive)

    def test_nonfinite_transforms_and_ambiguous_reverse_edges_are_rejected(self):
        # Configuration validation is run on a private scenario copy, leaving
        # authored geography unchanged.
        category = self.root / 'invalid/historical-world-rpg'
        project = category / 'age-of-sail-world'
        shutil.copytree(PROJECT, project, ignore=shutil.ignore_patterns('_build', '__pycache__'))
        shutil.copytree(PROJECT.parent / '_shared', category / '_shared', ignore=shutil.ignore_patterns('__pycache__'))
        path = project / 'scenario/maps/physical-boundaries.json'
        original = json.loads(path.read_text())
        for key, value in (('scale', float('inf')), ('offset', float('nan'))):
            invalid = copy.deepcopy(original)
            invalid['boundaries'][0]['arrivalTransform'][key] = value
            path.write_text(json.dumps(invalid))
            with self.assertRaisesRegex(PackagingError, 'arrival transform'):
                load_campaign_config(project / 'physical-maps.json')
        invalid = copy.deepcopy(original)
        duplicate = copy.deepcopy(invalid['boundaries'][1])
        duplicate.update(id='ambiguous_reverse', sourceEdge='south')
        invalid['boundaries'].append(duplicate)
        path.write_text(json.dumps(invalid))
        with self.assertRaisesRegex(PackagingError, 'ambiguous destination edge'):
            load_campaign_config(project / 'physical-maps.json')
