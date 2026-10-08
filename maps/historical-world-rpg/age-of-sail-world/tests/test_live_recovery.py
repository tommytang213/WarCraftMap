"""Generated recovery topology is evidence about the physical map, not fixtures."""
import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from boundary_arrival import components, playable_cells, verify_packaged_navigation
from recovery_navigation import recovery_navigation
from package_wurst_map import generate, load_config
from package_wurst_campaign import load_campaign_config
from materialize_physical_map import physical_layout


def component(grid, x, y):
    col = int((x - grid['minX']) // 128)
    row = int((y - grid['minY']) // 128)
    if not (0 <= col < grid['width'] and 0 <= row < grid['height']):
        return 0
    for run in grid['rows'][row].split(','):
        if run:
            end, label = map(int, run.split(':'))
            if col < end:
                return label
    return 0


class LiveRecoveryGeographyTests(unittest.TestCase):
    def test_disconnected_land_and_decorative_water_are_different_components(self):
        cells = [1, 1, 0, 1, 1,
                 2, 2, 0, 2, 2,
                 2, 2, 0, 2, 2]
        grids = recovery_navigation(5, 3, cells, (0, 0, 5, 3))
        for kind in range(4):
            labels = components(5, 3, cells, (0, 0, 5, 3), kind)
            self.assertEqual(2, len(set(labels) - {0}))
            for ident, x, y in grids[kind]['anchors']:
                self.assertEqual(ident, component(grids[kind], x, y))
        self.assertEqual(0, component(grids[0], -256, 0))
        self.assertEqual(0, component(grids[1], -256, -128))

    def test_all_generated_maps_prove_recovery_against_packaged_pathing(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            generate(load_config(PROJECT / 'package.json'), output)
            runtime = json.loads((output / 'scenario-runtime.json').read_text())
            source = (output / 'ScenarioData.wurst').read_text()
            # The authored world navigation fixtures must never enroll handles
            # or inject their coordinates into the physical recovery service.
            self.assertNotIn('new RecoveryEntity(', source)
            self.assertNotIn('service.importLastSafe(', source)
            config = load_campaign_config(PROJECT / 'physical-maps.json')
            seen = set()
            for physical in config.maps:
                if physical.bootstrap:
                    continue
                seen.add(physical.id)
                width, height, cells, _ = physical_layout(output, physical)
                info = (physical.source_map / 'war3map.w3i').read_bytes()
                # This is the same cell-to-WPM encoding used by materialization.
                values = {0: 0x4e, 1: 0x40, 2: 0x0a, 3: 0x4e}
                rows = []
                for row in range(height):
                    pixels = bytes(values[c] for c in cells[row*width:(row+1)*width] for _ in range(4))
                    rows.extend([pixels] * 4)
                wpm = b'MP3W' + struct.pack('<III', 0, width * 4, height * 4) + b''.join(rows)
                recovery = runtime['recoveryNavigation'][physical.id]
                verify_packaged_navigation(runtime['boundaryNavigation'], physical.id, info, wpm,
                                          runtime['partyNavigation'][physical.id], recovery)
                bad = copy.deepcopy(recovery)
                bad[0]['minX'] += 128
                with self.assertRaisesRegex(ValueError, 'recovery navigation'):
                    verify_packaged_navigation({}, physical.id, info, wpm, recovery=bad)
                # Land-party and recovery components have exactly one source.
                land = dict(recovery[0])
                land.pop('anchors')
                self.assertEqual(runtime['partyNavigation'][physical.id], land)
                for grid in recovery:
                    for ident, x, y in grid['anchors']:
                        self.assertEqual(ident, component(grid, x, y))
            self.assertEqual(seen, set(runtime['recoveryNavigation']))
            self.assertGreater(len({json.dumps(v) for v in runtime['recoveryNavigation'].values()}), 1)


if __name__ == '__main__':
    unittest.main()
