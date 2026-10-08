"""Static checks of the pinned compiler's Warcraft entry points.

This is a source/compiled-text contract, not Lua or Warcraft execution. Blizzard
initialization creates the shared forces, rectangles and game-start timer used
by campaign services. It does not initialize the terrain/unit lighting models.
The editor loads those separately before InitBlizzard. An incomplete source-map
main survives Wurst compilation. These checks do not prove native compatibility.
"""
from __future__ import annotations

import re

_LONG = re.compile(r"\[(=*)\[")
_TOKEN = re.compile(r"[A-Za-z_]\w*|.")


def _tokens(script: str) -> list[str]:
    # Keep strings as opaque tokens, so they cannot masquerade as calls but
    # literal native arguments can be checked. Ignore comments (including = levels).
    result, at = [], 0
    while at < len(script):
        comment = script.startswith("--", at)
        start = at + 2 if comment else at
        long = _LONG.match(script, start)
        if long:
            closing = "]" + long[1] + "]"
            end = script.find(closing, start + len(long[0]))
            at = len(script) if end < 0 else end + len(closing)
            if not comment:
                result.append(script[start:at])
        elif comment:
            end = script.find("\n", start)
            at = len(script) if end < 0 else end
        elif script[at] in "\"'":
            start = at
            quote = script[at]
            at += 1
            while at < len(script) and script[at] != quote:
                at += 2 if script[at] == "\\" else 1
            at += 1
            result.append(script[start:at])
        elif script[at].isspace():
            at += 1
        else:
            token = _TOKEN.match(script, at)[0]
            result.append(token)
            at += len(token)
    return result


def startup_failures(script: bytes | str) -> list[str]:
    """Require direct initialization in main, outside conditional/helper bodies.

    Accept the named function declarations emitted by the pinned compiler. This
    deliberately does not assert control-flow reachability or native success.
    """
    if isinstance(script, bytes):
        script = script.decode("utf-8")
    tokens = _tokens(script)
    failures = []
    # Only global declarations provide the entry points called by Warcraft.
    # A nested/local function with the right name is not an entry point.
    entries = {name: [] for name in ("config", "main")}
    depth = 0
    for i, token in enumerate(tokens):
        if token == "function" and depth == 0 and (i == 0 or tokens[i - 1] != "local"):
            if tokens[i + 1:i + 2] and tokens[i + 1] in entries and tokens[i + 2:i + 4] == ["(", ")"]:
                entries[tokens[i + 1]].append(i + 4)
        if token in ("function", "if", "do", "repeat"):
            depth += 1
        elif token in ("end", "until"):
            depth -= 1
    for name in ("config", "main"):
        starts = entries[name]
        if len(starts) != 1:
            failures.append(f"compiled Lua requires one {name} entry point")
            continue
        depth, calls, lighting = 1, [], []
        for i in range(starts[0], len(tokens)):
            token = tokens[i]
            if token in ("function", "if", "do", "repeat"):
                depth += 1
            elif token in ("end", "until"):
                depth -= 1
                if depth == 0:
                    break
            elif tokens[i + 1:i + 3] == ["(", ")"] and token == "InitBlizzard":
                calls.append((i, depth))
            elif token == "SetDayNightModels" and tokens[i + 1:i + 2] == ["("]:
                lighting.append((i, depth))
        else:
            failures.append(f"compiled Lua has an unterminated {name} entry point")
        if name == "config" and calls:
            failures.append("InitBlizzard must run in main, never in config")
        if name == "config" and lighting:
            failures.append("SetDayNightModels must run in main, never in config")
        if name == "main":
            if len(lighting) != 1 or lighting[0][1] != 1:
                failures.append("compiled Lua main must initialize terrain and unit lighting once before InitBlizzard")
            else:
                position = lighting[0][0]
                before = tokens[starts[0]:position]
                arguments = tokens[position + 1:position + 6]
                literal = lambda value: len(value) > 2 and value[0] in "\"'" and value[-1] == value[0]
                if (len(arguments) != 5 or arguments[0] != "(" or arguments[2] != ","
                        or arguments[4] != ")" or not literal(arguments[1]) or not literal(arguments[3])):
                    failures.append("SetDayNightModels requires two nonempty literal model paths")
                if (any(token in {"return", "goto", "if", "do", "repeat", "function",
                                  "and", "or", "SetDayNightModels"} or token.startswith("init_") for token in before)
                        or (before and before[-1] in {".", ":", "=", "(", ","})):
                    failures.append("SetDayNightModels must be an unconditional direct startup call")
                if calls and position > calls[0][0]:
                    failures.append("SetDayNightModels follows InitBlizzard")
            if len(calls) != 1 or calls[0][1] != 1:
                failures.append("compiled Lua main must call InitBlizzard once before Wurst package initialization")
            else:
                before = tokens[starts[0]:calls[0][0]]
                if any(token.startswith("init_") for token in before):
                    failures.append("InitBlizzard follows Wurst package initialization")
                # This is intentionally a conservative contract for the pinned
                # compiler's straight-line startup prelude, not a Lua control-
                # flow proof. Reject obvious bypasses and shadowed/member calls.
                if (any(token in {"return", "goto", "if", "do", "repeat", "function",
                                  "and", "or", "InitBlizzard"} for token in before)
                        or (before and before[-1] in {".", ":", "=", "(", ","})):
                    failures.append("InitBlizzard must be an unconditional direct startup call")
    return failures
