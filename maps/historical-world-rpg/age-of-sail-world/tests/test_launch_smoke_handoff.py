"""Regression tests for compiled-origin route evidence in handoff diagnostics.

These inspect compiler-shaped Lua text only. They never imply native Warcraft
campaign transition, destination startup, or responsive unit movement.
"""
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tooling"))
from stage_launch_smoke import _compiled_origin_routes, _require_compiled_origin_route  # noqa: E402
from warcraft_lua_startup import _tokens  # noqa: E402


EXPECTED = ("Archduchy of Austria", "europe_central_east", "EuropeCentralEast.w3x")


def compiled_selector(*, name=EXPECTED[0], map_id=EXPECTED[1], path=EXPECTED[2]):
    return (f'function main() OriginCatalog_OriginCatalog_add(controller2, "austria", '
            f'{name!r}, {map_id!r}, {path!r}, "europe_central_alpine", "vienna") end')


class CompiledHandoffRouteTests(unittest.TestCase):
    def test_actual_origin_call_must_bind_the_exact_austrian_destination(self):
        # Compile-shaped function call, not just a bag of strings found anywhere.
        tokens = _tokens(compiled_selector())
        self.assertEqual([EXPECTED], _compiled_origin_routes(tokens, "austria"))
        _require_compiled_origin_route(tokens, "austria", *EXPECTED)

    def test_unrelated_literals_and_commented_out_call_do_not_pass(self):
        script = ('-- OriginCatalog_OriginCatalog_add(controller, "austria", '
                  '"Archduchy of Austria", "europe_central_east", "EuropeCentralEast.w3x")\\n'
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
                tokens = _tokens(compiled_selector(**update) + '\\nprint("europe_central_east", "EuropeCentralEast.w3x", "Archduchy of Austria")')
                with self.assertRaisesRegex(ValueError, "mismatched austria route"):
                    _require_compiled_origin_route(tokens, "austria", *EXPECTED)

    def test_duplicate_austria_route_is_rejected(self):
        script = compiled_selector() + "\\n" + compiled_selector()
        tokens = _tokens(script)
        self.assertEqual([EXPECTED, EXPECTED], _compiled_origin_routes(tokens, "austria"))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            _require_compiled_origin_route(tokens, "austria", *EXPECTED)

    def test_other_polity_call_does_not_satisfy_austria(self):
        tokens = _tokens(compiled_selector().replace('"austria"', '"france"'))
        self.assertEqual([], _compiled_origin_routes(tokens, "austria"))
        with self.assertRaises(ValueError):
            _require_compiled_origin_route(tokens, "austria", *EXPECTED)


if __name__ == "__main__":
    unittest.main()
