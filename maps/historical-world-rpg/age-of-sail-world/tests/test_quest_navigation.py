"""Headless journal/map differential vectors consumed by pinned live execution."""
import importlib.util
from pathlib import Path
import unittest

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('quest_navigation_parity', PROJECT / 'reports/issue-476/parity.py')
parity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parity)


class QuestNavigationContractTests(unittest.TestCase):
    def test_exact_region_hidden_and_return_vectors_preserve_authority(self):
        values = parity.reference_vectors()
        self.assertEqual(('regional', 'europe', 'london', 'europe_printed_compact:london'), values['exact_local'])
        self.assertEqual(('regional', 'africa', 'timbuktu', ''), values['exact_unknown'])
        self.assertEqual(('regional', 'africa', '', ''), values['region'])
        self.assertEqual(('regional', 'europe', 'lisbon', 'europe_printed_compact:lisbon'), values['return'])
        for key in ('hidden', 'unmet_clue', 'approximate_unsupported'):
            self.assertEqual(('closed', '', '', ''), values[key])
        for key in ('visited_hidden', 'visited_approximate'):
            self.assertEqual(('regional', 'africa', 'timbuktu', ''), values[key])

    def test_differential_verifier_rejects_missing_or_fabricated_adapter_calls(self):
        with self.assertRaises(AssertionError):
            parity.verify_transcript('')
        values = parity.reference_vectors()
        rows = ['QUEST_MAP_VECTOR|' + name + '|' + '|'.join(row) for name, row in values.items()]
        parity.verify_transcript('\n'.join(rows))
        forged = '\n'.join(rows).replace('region|regional|africa||', 'region|regional|africa|timbuktu|')
        with self.assertRaises(AssertionError):
            parity.verify_transcript(forged)


if __name__ == '__main__':
    unittest.main()
