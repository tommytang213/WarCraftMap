"""Generated production contracts; gameplay arithmetic executes in Wurst."""
import json
import copy
from pathlib import Path
import sys
import tempfile
import unittest
import hashlib
from unittest.mock import patch

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'tooling'))
sys.path.insert(0,str(PROJECT.parent/'_shared/tooling'))
import agriculture_catalog
from package_wurst_map import generate, load_config, verify_generated, PackagingError
import package_wurst_map


class AgricultureGenerationTests(unittest.TestCase):
    def test_exact_approved_typed_identities_magnitudes_costs_and_eras(self):
        rules,effects=agriculture_catalog.build()
        self.assertEqual({('agrarian_improvement','building','granary',2000,1750),
                          ('agrarian_improvement','policy','land_tenure_reform',500,1750),
                          ('agricultural_mechanization','policy','enclosure',800,1780),
                          ('agricultural_societies','policy','progression_agricultural_societies',600,1720)},
                         {(x['nodeId'],x['kind'],x['contentId'],x['bonus'],x['earliestYear']) for x in effects})
        for row in effects:
            self.assertEqual(90,row['duration'])
            self.assertEqual(1000 if row['kind']=='building' else 100,row['costBp'])
            self.assertEqual(0 if row['kind']=='building' else 50,row['upkeepBp'])
        self.assertEqual(('grain','tools','timber'),tuple(rules[k] for k in ('stapleGoodId','equipmentGoodId','constructionGoodId')))
        enclosure=next(x for x in effects if x['contentId']=='enclosure')
        self.assertEqual((500,730),(enclosure['unrest'],enclosure['unrestDays']))

    def test_release_generation_includes_real_predicates_and_tracks_authored_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=load_config(PROJECT/'package.json')
            generate(config,Path(tmp))
            verify_generated(config,Path(tmp))
            source=(Path(tmp)/'ScenarioData.wurst').read_text()
            runtime=json.loads((Path(tmp)/'scenario-runtime.json').read_text())
            expected={(e['nodeId'],e['kind'],e['contentId']) for e in runtime['agriculture']['effects']}
            blockers={(e['nodeId'],e['kind'],e['contentId']) for e in runtime['researchIntegrationBlockers']}
            self.assertEqual(4,len(expected))
            self.assertFalse(expected & blockers)
            self.assertIn('import Agriculture',source)
            self.assertEqual(4,source.count('new AgricultureEffect('))
            # Grain merely sold/imported locally is not evidence of arable land.
            self.assertRegex(source,r'AgricultureSite\("aachen","[^"]+",\d+,\d+,0,40000,1000,\d+,false,false,false\)')
            self.assertRegex(source,r'AgricultureSite\("aberdeen","[^"]+",\d+,\d+,32,40000,1000,\d+,true,true,true\)')
            provenance=(Path(tmp)/'provenance.json').read_text()
            for path in ('scenario/progression/agriculture.json','scenario/progression/gameplay-effect-design.json','tooling/agriculture_catalog.py'):
                self.assertIn(path,provenance)
            # The designer's contracts and release blockers stay independently audited.
            design=json.loads((PROJECT/'scenario/progression/gameplay-effect-design.json').read_text())
            self.assertTrue(all(x['designStatus']=='approved_unimplemented' for x in design['effects']))

    def test_invalid_costs_rates_and_support_inputs_fail_before_generation(self):
        rules,_=agriculture_catalog.build()
        for key,value in [('policyCostBp',0),('seedFractionBp',10001),
                          ('constructionMaterials',-1),('policyDurationDays',False),
                          ('maximumKnowledge',1001)]:
            with self.subTest(key=key):
                candidate=copy.deepcopy(rules)
                candidate[key]=value
                with self.assertRaises(ValueError):
                    agriculture_catalog.validate_rules(candidate)

    def test_resealed_omitted_or_duplicate_registrations_and_disconnected_configuration_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            config=load_config(PROJECT/'package.json')
            generate(config,root)
            source=(root/'ScenarioData.wurst').read_text()
            runtime=(root/'scenario-runtime.json').read_text()
            registration=next(line for line in source.splitlines() if 'runtime.agriculture.addEffect(' in line)
            for changed in (source.replace(registration+'\n',''),
                            source.replace(registration,registration+'\n'+registration),
                            source.replace('configureGeneratedAgriculture(runtime)','skip')):
                with self.subTest(change=changed!=source):
                    (root/'ScenarioData.wurst').write_text(changed)
                    provenance=json.loads((root/'provenance.json').read_text())
                    provenance['outputs']['ScenarioData.wurst']=hashlib.sha256(changed.encode()).hexdigest()
                    (root/'provenance.json').write_text(json.dumps(provenance))
                    with self.assertRaisesRegex(PackagingError,'agriculture bindings'):
                        verify_generated(config,root)
            (root/'ScenarioData.wurst').write_text(source)
            damaged=json.loads(runtime)
            damaged['agriculture']['effects'].pop()
            (root/'scenario-runtime.json').write_text(json.dumps(damaged))
            provenance=json.loads((root/'provenance.json').read_text())
            for name in ('ScenarioData.wurst','scenario-runtime.json'):
                provenance['outputs'][name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
            (root/'provenance.json').write_text(json.dumps(provenance))
            with self.assertRaisesRegex(PackagingError,'agriculture bindings'):
                verify_generated(config,root)

    def test_generator_does_not_recognize_omitted_agriculture_registrations(self):
        # Compiler protocol mutation only, never release evidence. Omitted
        # builder effects must stay unrecognized in the generated metadata.
        original=package_wurst_map.subprocess.check_output
        def missing(command, **kwargs):
            value=original(command,**kwargs)
            if str(command[1]).endswith('/tooling/agriculture_catalog.py'):
                data=json.loads(value)
                data['effects']=[]
                data['wurst']=[]
                return json.dumps(data)
            return value
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(package_wurst_map.subprocess,'check_output',side_effect=missing):
                generate(load_config(PROJECT/'package.json'),Path(tmp))
            data=json.loads((Path(tmp)/'scenario-runtime.json').read_text())
            blockers={(e['nodeId'],e['kind'],e['contentId']) for e in data['researchIntegrationBlockers']}
            _,effects=agriculture_catalog.build()
            self.assertTrue({(e['nodeId'],e['kind'],e['contentId']) for e in effects} <= blockers)
