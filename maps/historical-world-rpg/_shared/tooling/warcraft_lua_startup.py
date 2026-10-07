"""Static checks of the pinned compiler's Warcraft entry points.

This is a source/compiled-text contract, not Lua or Warcraft execution. Blizzard
initialization creates the shared forces, rectangles and game-start timer used
by campaign services. An empty source-map main survives Wurst compilation.
"""
from __future__ import annotations

import re

_LONG = re.compile(r"\[(=*)\[")
_TOKEN = re.compile(r"[A-Za-z_]\w*|.")


def _tokens(script: str) -> list[str]:
    # Ignore quoted strings and Lua long strings/comments (including = levels).
    result, at = [], 0
    while at < len(script):
        comment = script.startswith("--", at)
        start = at + 2 if comment else at
        long = _LONG.match(script, start)
        if long:
            closing = "]" + long[1] + "]"
            end = script.find(closing, start + len(long[0]))
            at = len(script) if end < 0 else end + len(closing)
        elif comment:
            end = script.find("\n", start)
            at = len(script) if end < 0 else end
        elif script[at] in "\"'":
            quote = script[at]
            at += 1
            while at < len(script) and script[at] != quote:
                at += 2 if script[at] == "\\" else 1
            at += 1
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
        depth, calls = 1, []
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
        else:
            failures.append(f"compiled Lua has an unterminated {name} entry point")
        if name == "config" and calls:
            failures.append("InitBlizzard must run in main, never in config")
        if name == "main":
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
