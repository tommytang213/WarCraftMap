"""Regression tests for compiled-origin route evidence in handoff diagnostics.

These inspect compiler-shaped Lua text only. They never imply native Warcraft
campaign transition, destination startup, or responsive unit movement.
"""
import json
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tooling"))
from stage_launch_smoke import (  # noqa: E402
    _compiled_origin_definitions, _compiled_origin_routes,
    _require_compiled_origin_route, _require_compiled_origin_catalog,
)
from warcraft_lua_startup import _tokens  # noqa: E402


EXPECTED = ("Archduchy of Austria", "europe_central_east", "EuropeCentralEast.w3x")


def compiled_selector(*, polity_id="austria", name=EXPECTED[0], map_id=EXPECTED[1],
                      path=EXPECTED[2], instance="europe_central_alpine", settlement="vienna"):
    values = (polity_id, name, map_id, path, instance, settlement)
    return ('function main() OriginCatalog_OriginCatalog_add(controller2, '
            + ", ".join(json.dumps(value) for value in values) + ') end')


class CompiledHandoffRouteTests(unittest.TestCase):
    def test_actual_origin_call_must_bind_the_exact_austrian_destination(self):
        # Compile-shaped function call, not just a bag of strings found anywhere.
        tokens = _tokens(compiled_selector())
        self.assertEqual([EXPECTED], _compiled_origin_routes(tokens, "austria"))
        _require_compiled_origin_route(tokens, "austria", *EXPECTED)

    def test_unrelated_literals_and_commented_out_call_do_not_pass(self):
        script = ('-- OriginCatalog_OriginCatalog_add(controller, "austria", '
                  '"Archduchy of Austria", "europe_central_east", "EuropeCentralEast.w3x")\n'
                  'function main() print("austria") print("europe_central_east") '
                  'print("EuropeCentralEast.w3x") end')
        tokens = _tokens(script)
        self.assertEqual([], _compiled_origin_routes(tokens, "austria"))
        with self.assertRaisesRegex(ValueError, "missing, duplicate, or mismatched austria route"):
            _require_compiled_origin_route(tokens, "austria", *EXPECTED)

    def test_wrong_destination_id_or_path_is_rejected_even_with_expected_strings_elsewhere(self):
        for field, update in (("map", {"map_id": "europe_west"}),
                              ("path", {"path": "EuropeWest.w3x"}),
                              ("name", {"name": "Wrong country"})):
            with self.subTest(field=field):
                # The expected strings appear elsewhere, but not as the
                # arguments of the actual Austrian origin registration.
                tokens = _tokens(compiled_selector(**update) + '\nprint("europe_central_east", "EuropeCentralEast.w3x", "Archduchy of Austria")')
                with self.assertRaisesRegex(ValueError, "mismatched austria route"):
                    _require_compiled_origin_route(tokens, "austria", *EXPECTED)

    def test_duplicate_austria_route_is_rejected(self):
        script = compiled_selector() + "\n" + compiled_selector()
        tokens = _tokens(script)
        self.assertEqual([EXPECTED, EXPECTED], _compiled_origin_routes(tokens, "austria"))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            _require_compiled_origin_route(tokens, "austria", *EXPECTED)

    def test_other_polity_call_does_not_satisfy_austria(self):
        tokens = _tokens(compiled_selector().replace('"austria"', '"france"'))
        self.assertEqual([], _compiled_origin_routes(tokens, "austria"))
        with self.assertRaises(ValueError):
            _require_compiled_origin_route(tokens, "austria", *EXPECTED)


    def test_full_compiled_catalog_matches_every_origin_start_field(self):
        austria = (*EXPECTED, "europe_central_alpine", "vienna")
        england = ("Kingdom of England", "europe_west", "EuropeWest.w3x",
                   "europe_atlantic_isles", "london")
        script = compiled_selector() + "\n" + compiled_selector(
            polity_id="england", name=england[0], map_id=england[1],
            path=england[2], instance=england[3], settlement=england[4])
        self.assertEqual(2, _require_compiled_origin_catalog(
            _tokens(script), {"austria": austria, "england": england}))

    def test_wrong_instance_or_settlement_is_not_valid_handoff_evidence(self):
        expected = {"austria": (*EXPECTED, "europe_central_alpine", "vienna")}
        for change in ({"instance": "europe_atlantic_isles"},
                       {"settlement": "london"}):
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError, "authoritative start records"):
                    _require_compiled_origin_catalog(_tokens(compiled_selector(**change)), expected)

    def test_missing_duplicate_or_extra_compiled_origin_is_rejected(self):
        expected = {"austria": (*EXPECTED, "europe_central_alpine", "vienna")}
        examples = ("function main() end",
                    compiled_selector() + "\n" + compiled_selector(),
                    compiled_selector() + "\n" + compiled_selector(polity_id="unknown"))
        for script in examples:
            with self.subTest(script=script[:40]):
                with self.assertRaisesRegex(ValueError, "authoritative start records"):
                    _require_compiled_origin_catalog(_tokens(script), expected)

    def test_partial_or_dynamic_compiled_origin_registration_cannot_pass(self):
        examples = (
            compiled_selector().replace(', "europe_central_alpine", "vienna"', ''),
            compiled_selector().replace('"europe_central_alpine"', 'runtimeInstance'),
        )
        for script in examples:
            with self.subTest(script=script[-60:]):
                with self.assertRaisesRegex(ValueError, "origin registration"):
                    _compiled_origin_definitions(_tokens(script))

    def test_function_declaration_is_not_an_origin_registration(self):
        declaration = ("function OriginCatalog_OriginCatalog_add(controller, polity, "
                       "name, mapId, packagePath, instance, settlement) end\n")
        actual = _compiled_origin_definitions(_tokens(declaration + compiled_selector()))
        self.assertEqual([("austria", *EXPECTED, "europe_central_alpine", "vienna")],
                         actual)


if __name__ == "__main__":
    unittest.main()
