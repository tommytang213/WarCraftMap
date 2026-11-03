"""One-variable native diagnostic: omit execution of Wurst package initializers.

Not a repair. Root chunk, config, all function definitions and main's existing
bootstrap/global/compile-time/lighting/Blizzard prelude stay byte-identical.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re

BASELINE_SHA256 = "efaffe67682ca0c3c952722ce0a5f42be1ba954a27c5ad49177f48b6c536ebe3"
INITIALIZERS = (
    "AbilityIds Angle Real Integer Maths String Vectors Destructable Player Basics "
    "Printing MagicFunctions GameTimer ErrorHandling Matrices Quaternion Table Force "
    "Playercolor Colors Framehandle Group Lightning WeatherEffects TypeCasting HashList "
    "EventHelper RuntimeProtection WC3Compatibility CommandRouter ScenarioData "
    "CampaignSaveManager ScenarioSettings CampaignHandoff Bootstrap"
).split()
MAIN = b"function main() \n"
CONFIG = b"function config() \n"
TAIL = b"\tif not xpcall(init_AbilityIds,"
MARKERS = b'''\tDisplayTimedTextToPlayer(Player(0), 0., 0., 120., "438: main tail reached")
\tlocal diagnosticTimer = CreateTimer()
\tTimerStart(diagnosticTimer, 0., false, function()
\t\tDestroyTimer(GetExpiredTimer())
\t\tDisplayTimedTextToPlayer(Player(0), 0., 0., 120., "438: timer reached")
\tend)
end

'''


def isolation_script(baseline: bytes) -> bytes:
    if hashlib.sha256(baseline).hexdigest() != BASELINE_SHA256:
        raise ValueError("expected exact failing smoke #3 Lua SHA-256")
    if baseline.count(MAIN) != 1 or baseline.count(CONFIG) != 1:
        raise ValueError("expected exactly one main and config declaration")
    main = baseline.index(MAIN)
    config = baseline.index(CONFIG, main + len(MAIN))
    body = baseline[main:config]
    if body.count(TAIL) != 1 or not body.endswith(b"end\n\n"):
        raise ValueError("unexpected pinned main boundary")
    initializers = re.findall(rb"xpcall\(init_(\w+),", body)
    if initializers != [name.encode() for name in INITIALIZERS]:
        raise ValueError("unexpected pinned package initializer sequence")
    tail = main + body.index(TAIL)
    prelude = baseline[main:tail]
    if prelude.count(b"\tSetDayNightModels(") != 1 or prelude.count(b"\tInitBlizzard()\n") != 1:
        raise ValueError("missing native startup spine")
    result = baseline[:tail] + MARKERS + baseline[config:]
    if result == baseline:
        raise ValueError("diagnostic must materially differ from failing script")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = isolation_script(args.baseline.read_bytes())
    if args.output.exists():
        parser.error("output already exists; refusing to overwrite evidence")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    print(hashlib.sha256(result).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
