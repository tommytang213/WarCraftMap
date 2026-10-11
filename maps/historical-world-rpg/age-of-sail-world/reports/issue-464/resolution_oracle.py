"""Independent Fraction-oracle checks for executed typed tradition layers."""
from fractions import Fraction
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2].parent / "_shared/engine"))
from military_tradition import MilitaryTraditionRuntime, RecordingTraditionAdapter


def verify_vectors(definitions: dict, transcript: str) -> dict:
    def records(prefix):
        return [json.loads(line[len(prefix):]) for line in transcript.splitlines() if line.startswith(prefix)]

    vectors = records("RESOLVED_TRADITION_ORACLE ")
    rationals = records("RATIONAL_TRADITION_ORACLE ")
    assert vectors and rationals, "missing executed resolution vectors"
    for row in vectors:
        oracle = MilitaryTraditionRuntime(definitions, RecordingTraditionAdapter())
        oracle.change_unit("english_guard_formation", controller_id=row["controller"], category_id=row["category"])
        state = oracle.snapshot()
        next(track for track in state["tracks"] if (track["controllerId"], track["categoryId"]) ==
             (row["controller"], row["category"]))["experience"] = int(row["before"])
        oracle.restore(state)
        oracle.award([dict(sourceId="enemy_kill", unitId="english_guard_formation",
                           enemyControllerId="england" if row["controller"] == "france" else "france", amount=1)])
        expected = oracle.view(row["controller"], row["category"])
        assert int(row["experience"]) == expected.experience
        assert {key: Fraction(int(value[0]), int(value[1])) for key, value in row["modifiers"].items()} == expected.modifiers
        # Also require canonical reduction and signs, for exact inspection.
        assert row["modifiers"] == {key: [str(value.numerator), str(value.denominator)]
                                    for key, value in expected.modifiers.items()}
        assert tuple(filter(None, row["effects"].split(","))) == expected.effects
        tradition = next(t for t in definitions["traditions"] if t["categoryId"] == row["category"])
        reached = [m["id"] for m in sorted(tradition["milestones"], key=lambda m: (m["threshold"], m["id"]))
                   if m["threshold"] <= expected.experience]
        assert list(filter(None, row["reached"].split(","))) == reached
    for row in rationals:
        expected = int(row["xp"]) * Fraction(*map(int, row["coefficient"]))
        assert row["value"] == [str(expected.numerator), str(expected.denominator)]
    assert {r["controller"] for r in vectors} == {"player", "france"}
    assert {r["category"] for r in vectors} == {t["categoryId"] for t in definitions["traditions"]}
    for tradition in definitions["traditions"]:
        experience = {int(row["experience"]) for row in vectors if row["category"] == tradition["categoryId"]}
        assert {1, 2, 2147483648, 9007199254740992, 9007199254740993} <= experience
        assert max(experience) > 10**60
        for milestone in tradition["milestones"]:
            assert {milestone["threshold"] + offset for offset in (-1, 0, 1)} <= experience
    return {"resolvedLayerVectors": vectors, "rationalVectors": rationals}
