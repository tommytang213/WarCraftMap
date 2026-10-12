"""Compare recorded live map/marker adapter calls with both headless contracts."""
import copy
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT.parent / '_shared/engine'))
from quest_journal import QuestJournal
from map_discovery import CampaignMap, DiscoveryKnowledge, MapDiscoveryError


def reference_vectors():
    locations = [dict(id=ident, name=ident, kind='settlement', regionId=region,
                      position=dict(x=10 + index, y=20 + index))
                 for index, (ident, region) in enumerate(
                     [('lisbon', 'europe'), ('london', 'europe'), ('timbuktu', 'africa')])]
    geography = dict(regions=[dict(id='europe'), dict(id='africa')], boundaries=[], routes=[])
    catalog = dict(geography, settlements=locations, landmarks=[], pointsOfInterest=[])
    result = {}
    cases = [
        ('exact_local', 'exact', 'london', False, False, False),
        ('exact_unknown', 'exact', 'timbuktu', False, False, False),
        ('region', 'region', 'timbuktu', False, False, False),
        ('hidden', 'hidden', 'timbuktu', False, False, False),
        ('approximate_unsupported', 'approximate', 'timbuktu', False, False, False),
        ('visited_approximate', 'approximate', 'timbuktu', True, False, False),
        ('visited_hidden', 'hidden', 'timbuktu', True, False, False),
        ('unmet_clue', 'hidden', 'timbuktu', True, True, False),
        ('return', 'exact', 'london', False, False, True),
    ]
    for name, precision, destination, visited, clue, ready in cases:
        region = next(x['regionId'] for x in locations if x['id'] == destination)
        goal = dict(precision=precision, regionId=region, locationId=destination,
                    requiredClueIds=['missing_clue'] if clue else [],
                    searchAreas=[dict(x=10, y=20, radius=100)] if precision == 'approximate' else [])
        quest = dict(id='europe_printed_compact', initialStageId='work',
                     stages=[dict(id='work', objectiveIds=['go'], nextStageIds=[])],
                     objectives=[dict(id='go')], journal=dict(destinations={'go': goal},
                     turnInDestination=dict(precision='exact', regionId='europe', locationId='lisbon')))
        state = dict(id=quest['id'], status='active', stageId='work',
                     completedObjectiveIds=['go'] if ready else [])
        journal = QuestJournal(dict(quests=[quest]), geography, locations)
        knowledge = DiscoveryKnowledge(catalog)
        knowledge.visit_settlement('lisbon')
        if visited:
            journal.discover_location(destination)
            knowledge.visit_settlement(destination)
        screen = CampaignMap(catalog, knowledge, 'europe', 'europe')
        before = copy.deepcopy((state, journal.snapshot(), knowledge.export_state()))
        entry = journal._entry(quest['id'], state, 'europe')
        guidance = entry['guidance']
        # Approximate is supported headlessly but deliberately remains unavailable
        # in this live scope. Its authored search area must never become a point.
        if guidance and guidance['precision'] == 'approximate':
            area = journal.show_on_map(quest['id'], state, physical_region_id='europe', campaign_map=screen)
            assert area['focus']['targetId'] is None and area['focus']['areas']
            result[name] = ('closed', '', '', '')
        elif entry['actions']['showOnMap']:
            view = journal.show_on_map(quest['id'], state, physical_region_id='europe', campaign_map=screen)
            target = view['focus']['targetId'] or ''
            marker = quest['id'] + ':' + target if target and view['focusedRegionId'] == 'europe' else ''
            result[name] = (view['context'], view['focusedRegionId'], target, marker)
            if not visited and region == 'africa':
                focused = screen.focus
                try:
                    screen.open_region('africa')
                except MapDiscoveryError:
                    pass
                else:
                    raise AssertionError('quest focus leaked ordinary region authorization')
                assert screen.focus == focused
                assert not view['settlements'] and not view['pointsOfInterest']
        else:
            result[name] = ('closed', '', '', '')
        assert before == (state, journal.snapshot(), knowledge.export_state())
    return result


def verify_transcript(transcript):
    actual = {}
    for line in transcript.splitlines():
        if line.startswith('QUEST_MAP_VECTOR|'):
            _, name, *values = line.split('|')
            assert name not in actual, 'duplicate live vector'
            actual[name] = tuple(values)
    expected = reference_vectors()
    assert actual == expected, dict(expected=expected, actual=actual)
    return sorted(expected)
