"""Source-contract checks for dormant institutional-court integration.

These inspect actual Wurst source and evaluate only its pure version predicate.
They are NOT Wurst execution, military snapshot round trips, or native gameplay.
Behavioral regression cases live in InstitutionCourtLifecycleTests.wurst.
"""
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "_shared/wurst/MilitarySettlementRuntime.wurst"


def method(source: str, name: str) -> str:
    match = re.search(r"(?m)^\tfunction " + re.escape(name) + r"\([^\n]*\n", source)
    if not match:
        raise AssertionError(f"Missing method: {name}")
    start = match.start()
    end = re.search(r"(?m)^\t(?:function |override function |/\*\*|ondestroy)|^public ", source[match.end():])
    return source[start:match.end() + end.start()] if end else source[start:]


def required_expression(source: str) -> ast.expr:
    match = re.search(
        r"public function militaryInstitutionCourtsRequired\(string candidate\) returns boolean\n\treturn ([^\n]+)",
        source,
    )
    if not match:
        raise AssertionError("Missing court-version predicate")
    return ast.parse(match.group(1), mode="eval").body


def evaluate(node: ast.expr, candidate: str) -> bool:
    """Allow only Boolean operations and two literal-string predicate calls."""
    if isinstance(node, ast.BoolOp):
        values = [evaluate(child, candidate) for child in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not evaluate(node.operand, candidate)
    elif isinstance(node, ast.Call) and not node.keywords and len(node.args) == 1:
        function = node.func
        arg = node.args[0]
        if (isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name)
                and function.value.id == "candidate" and isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)):
            if function.attr == "startsWith":
                return candidate.startswith(arg.value)
            if function.attr == "contains":
                return arg.value in candidate
    raise AssertionError(f"Unsupported predicate syntax: {ast.dump(node)}")


class InstitutionCourtStagingSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_current_version_and_accepted_headers_remain_v20(self):
        self.assertIn("public constant int MILITARY_SETTLEMENT_SNAPSHOT_VERSION = 20\n", self.source)
        first_guard = method(self.source, "parseSnapshot").split("\n")[1]
        versions = {int(value) for value in re.findall(r'candidate.startsWith\("v(\d+)\|"\)', first_guard)}
        self.assertEqual(set(range(1, 21)), versions)
        self.assertIn("candidate.endsWith", first_guard)

    def test_customs_boundary_truth_table_from_actual_source(self):
        predicate = required_expression(self.source)
        for version in range(1, 27):
            for customs in (False, True):
                for court in (False, True):
                    with self.subTest(version=version, customs=customs, court=court):
                        candidate = f"v{version}|k,0" + ("|J,0" if customs else "") + ("|O,port,,0,0,0,0" if court else "")
                        expected = version == 26 or (version == 25 and not customs) or court
                        self.assertEqual(expected, evaluate(predicate, candidate))
        self.assertFalse(evaluate(predicate, "v20|o,port|j,site"))
        self.assertTrue(evaluate(predicate, "v25|j,site"))

    def test_source_predicate_evaluator_rejects_arbitrary_execution(self):
        for expression in ("__import__('os')", "candidate.lower()", "candidate.contains(candidate)", "candidate[0]"):
            with self.subTest(expression=expression), self.assertRaises(AssertionError):
                evaluate(ast.parse(expression, mode="eval").body, "v20|k,0")

    def test_writer_is_version_gated_and_does_not_select_a_new_schema(self):
        writer = method(self.source, "institutionCourtRecords")
        self.assertIn("if snapshotVersion >= 25\n", writer)
        self.assertIn('result += "|O,"', writer)
        self.assertIn("result += institutionCourtRecords(MILITARY_SETTLEMENT_SNAPSHOT_VERSION)", method(self.source, "snapshot"))
        self.assertNotIn('"|O,"', method(self.source, "snapshot"))

    def test_ledger_is_owned_forked_and_detached_after_transfer(self):
        self.assertIn("BankingLedger institutionCourts = new BankingLedger()", self.source)
        self.assertEqual(2, self.source.count("\t\tdestroy institutionCourts\n"))
        parser = method(self.source, "parseSnapshot")
        self.assertIn("destroy parsed.institutionCourts\n\t\tparsed.institutionCourts = institutionCourts.fork()", parser)
        self.assertIn('parsed.legacyInstitutionCourts = not candidate.startsWith("v25|") and not candidate.startsWith("v26|")', parser)
        transfer = "institutionCourts = parsed.institutionCourts\n\t\tparsed.institutionCourts = new BankingLedger()\n\t\tlegacyInstitutionCourts = parsed.legacyInstitutionCourts"
        self.assertIn(transfer, self.source)
        transfer_at = self.source.index(transfer)
        self.assertLess(transfer_at, self.source.index("\t\tdestroy parsed\n", transfer_at))
        self.assertIn("institutionCourts.controlChanged(settlementId)", method(self.source, "transferSettlement"))

    def test_record_rejections_precede_every_state_write(self):
        body = method(self.source, "restoreInstitutionCourtRecord")
        self.assertIn("if legacyInstitutionCourts or i < 0 or institutionCourts.states[i].restored", body)
        self.assertIn('scienceControllerText(owner)', body)
        self.assertEqual(4, body.count("militaryCourtInteger("))
        self.assertIn('(through - ready) mod 365 == 0', body)
        self.assertIn('through > day', body)
        first_write = body.index("state.owner = owner")
        self.assertGreater(first_write, body.rindex("return false"))
        self.assertGreater(body.index("state.restored = true"), first_write)
        self.assertIn('exactNaturalCompare(value, "2147483647") <= 0', self.source)
        dispatch = method(self.source, "restoreSnapshotRecord")
        self.assertIn('if kind == "O"\n\t\t\tif record.count != 7\n\t\t\t\treturn false', dispatch)
        self.assertIn("return target.restoreInstitutionCourtRecord(record.field(1), record.field(2), record.field(3), record.field(4), record.field(5), record.field(6))", dispatch)

    def test_completeness_control_and_day_checks_are_connected(self):
        body = method(self.source, "validateInstitutionCourts")
        self.assertIn("let required = militaryInstitutionCourtsRequired(candidate)", body)
        self.assertIn("required and not state.restored", body)
        self.assertIn("settlements[city].controllerId != state.owner", body)
        self.assertIn("campaignDay >= 0 and state.lastDay > campaignDay", body)
        self.assertIn("if not parsed.validateInstitutionCourts(candidate, -1)\n\t\t\tparsed.dispose()\n\t\t\treturn null", method(self.source, "parseSnapshot"))
        self.assertIn("if not parsed.validateInstitutionCourts(candidate, campaignDay)\n\t\t\tparsed.dispose()\n\t\t\treturn null", method(self.source, "parseValidatedSnapshot"))


if __name__ == "__main__":
    unittest.main()
