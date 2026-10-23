"""Fail-closed selection protocol; these fixtures are never release evidence."""
import copy
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'tooling'))
sys.path.insert(0,str(PROJECT.parent/'_shared/tooling'))
import agriculture_catalog as agriculture
import release_blocker_audit as release
from integration_evidence import load_contract, instrument, execution_sources
from wurst_execution import discover

PREFIX='wurst/AgricultureTests.wurst:'
FINDINGS={
    'RESEARCH-UNBOUND-AGRARIAN-IMPROVEMENT-BUILDING-GRANARY',
    'RESEARCH-UNBOUND-AGRARIAN-IMPROVEMENT-POLICY-LAND-TENURE-REFORM',
    'RESEARCH-UNBOUND-AGRICULTURAL-MECHANIZATION-POLICY-ENCLOSURE',
    'RESEARCH-UNBOUND-AGRICULTURAL-SOCIETIES-POLICY-PROGRESSION-AGRICULTURAL-SOCIETIES',
}


def selection_evidence():
    contract=load_contract(PROJECT)
    return {'tests':[{'id':PREFIX+n,'status':'pass'} for n in sorted(agriculture.REQUIRED_TESTS)],
            'productionCoverage':{'tests':{PREFIX+n:list(contract['probes']) for n in agriculture.REQUIRED_TESTS}}}


class AgricultureEvidenceTests(unittest.TestCase):
    def findings(self, report=None):
        return {r['id'] for r in release._audit_research_bindings(
            execution=report,execution_log=b'protocol fixture',revision='a'*40)}

    def test_definitions_and_runtime_labels_never_establish_release_closure(self):
        self.assertTrue(FINDINGS <= self.findings())
        self.assertEqual(set(),agriculture.verified_bindings(PROJECT,{},b'', 'a'*40))
        self.assertEqual(set(),agriculture.verified_bindings(PROJECT,selection_evidence(),b'fake', 'a'*40))

    def test_only_four_exact_findings_clear_with_verified_production_comparisons(self):
        baseline=self.findings()
        report=selection_evidence()
        # Mock only the separately tested cryptographic/transcript verifier;
        # the release audit and agriculture test/probe selection remain real.
        with patch('integration_evidence.verify_execution_coverage',return_value={}):
            self.assertEqual(baseline-FINDINGS,self.findings(report))
            for name in agriculture.REQUIRED_TESTS:
                changed=copy.deepcopy(report)
                next(r for r in changed['tests'] if r['id']==PREFIX+name)['status']='fail'
                self.assertEqual(baseline,self.findings(changed),name)
                changed['tests']=[r for r in changed['tests'] if r['id']!=PREFIX+name]
                self.assertEqual(baseline,self.findings(changed),name)

    def test_each_disconnected_comparative_callback_and_registration_retains_exact_findings(self):
        report=selection_evidence()
        baseline=self.findings()
        cases={n:agriculture.PRODUCTION_PROBES for n in agriculture.COMPARATIVE_TESTS}
        cases['agriculturalSocietiesSeparateDiffusionAndConditionalFarmOutput']=agriculture.PRODUCTION_PROBES|{'agriculture_adoption'}
        cases['agriculturalProductionRegistrationConnectsResearchClockAndMarkets']={
            'domains','agriculture_definitions','agriculture_layers','agriculture_clock',
            'agriculture_advance','agriculture_storage'}
        with patch('integration_evidence.verify_execution_coverage',return_value={}):
            for name,probes in cases.items():
                for probe in probes:
                    with self.subTest(test=name,probe=probe):
                        changed=copy.deepcopy(report)
                        changed['productionCoverage']['tests'][PREFIX+name].remove(probe)
                        self.assertEqual(baseline,self.findings(changed))
            report.pop('productionCoverage')
            self.assertEqual(baseline,self.findings(report))

    def test_missing_failed_or_stale_evidence_always_retains_exact_findings(self):
        for reason in ('missing source identity','stale source revision','failed compiler',
                       'stale generated input','declared coverage differs from transcript'):
            with self.subTest(reason=reason), patch('integration_evidence.verify_execution_coverage',side_effect=ValueError(reason)):
                self.assertTrue(FINDINGS <= self.findings(selection_evidence()))

    def test_authored_probes_target_real_unique_production_bodies(self):
        sources=execution_sources(PROJECT)
        contract=load_contract(PROJECT)
        self.assertEqual(agriculture.PRODUCTION_PROBES | {'agriculture_adoption'},
                         set(contract['systems']['agriculture']))
        self.assertEqual(agriculture.REQUIRED_TESTS,
                         {t['id'][len(PREFIX):] for t in discover(PROJECT, sources=sources)
                          if t['id'].startswith(PREFIX)})
        for name,spec in contract['probes'].items():
            if name.startswith('agriculture_') and spec['path'] in sources:
                text=instrument(sources[spec['path']].read_text(),{name:spec})
                self.assertEqual(1,text.count('print("WCM_PROBE:'+name+'")'))
