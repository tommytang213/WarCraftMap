#!/usr/bin/env python3
"""Audit content literals and prohibit private copies of shared mechanisms.

The vocabulary comes from authored catalogues, not a hand-maintained list of
historical names. Python comments/docstrings and Wurst comments are excluded;
executable strings and identifiers (including conditions) are checked. Neutral
schema words that happen to be content IDs require an exact, reviewed exception.
"""
import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import re
import tokenize

from scenario_inputs import configuration

EXTENSIONS = {".py", ".wurst", ".lua", ".j"}


def code_tokens(path):
    source = path.read_text(encoding="utf-8")
    if path.suffix == ".py":
        tree = ast.parse(source)
        docstrings = set()
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if isinstance(body, list) and body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                docstrings.add((body[0].lineno, body[0].end_lineno))
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type in {tokenize.STRING, tokenize.NAME} and not any(a <= token.start[0] <= b for a, b in docstrings):
                yield token.start[0], token.string
    else:
        # Preserve newlines for actionable diagnostics; don't strip comment-like
        # substrings inside string literals.
        pattern = r'"(?:\\.|[^"\\])*"|\'[^\'\n]*\'|//[^\n]*|/\*[\s\S]*?\*/|[A-Za-z_][A-Za-z0-9_]*'
        for token in re.finditer(pattern, source):
            if not token[0].startswith(("//", "/*")):
                yield source.count("\n", 0, token.start()) + 1, token[0]


def vocabulary(project):
    config = configuration(project)
    world = json.loads((project / config["scenario"]["data"]).read_text())
    result = {project.name, project.name.replace("-", "_"),
              config["release"]["metadata"]["name"], config["release"]["fileName"]}
    if config["release"].get("cacheFile"):
        result.add(config["release"]["cacheFile"])
    manifest = project / "physical-maps.json"
    if manifest.is_file():
        physical = json.loads(manifest.read_text())
        result.update(physical["campaign"][key] for key in ("id", "fileName", "name"))
        result.update(row["id"] for row in physical["physicalMaps"])
    for domain in ("polities", "settlements", "characters", "quests", "personalQuests", "events"):
        for row in world.get(domain, []):
            result.update(row[key] for key in ("id", "name", "displayName", "title") if row.get(key))
    goods = project / "scenario/economy/global-goods.json"
    if goods.is_file():
        for row in json.loads(goods.read_text()).get("goods", []):
            result.update(row[key] for key in ("id", "name") if row.get(key))
    # Maps, regions and fixture namespaces are also scenario decisions.
    for row in world.get("regionalGeography", {}).get("regions", []):
        result.update((row["id"], row["name"]))
    # Test-authored rename rules also own their namespaces. A prefix-based
    # special case or a branch on a mutated ID is still scenario coupling.
    mutation = project / "mutation.json"
    if mutation.is_file():
        replacements = json.loads(mutation.read_text())["replacements"]
        for value in list(result):
            for before, after in replacements.items():
                value = value.replace(before, after)
            result.add(value)
        result.update(replacements)
        result.update(replacements.values())
    return {value.casefold() for value in result if len(value) >= 3}


def mechanism_fingerprints(path):
    """Overlapping statement windows catch a renamed or lightly edited fork."""
    tokens = []
    for _, token in code_tokens(path):
        if token.startswith(('"', "'")):
            tokens.append("STRING")
        else:
            tokens.append(token)
    # Ignore short glue and signatures. Check every offset: sampling both files
    # would miss a fork after adding an import or another statement at its start.
    # Compact digests keep indexing all overlapping windows inexpensive.
    return {hashlib.sha256("\0".join(tokens[i:i + 80]).encode()).digest()
            for i in range(len(tokens) - 79)}


def boundary_tokens(path):
    """Check literal values as well as spelling, retaining exact exceptions.

    Python joins adjacent string literals and decodes escapes before a branch
    executes. Those constants must not hide a content dependency from the audit.
    Wurst's quoted strings can also contain JSON-style escapes.
    """
    for line, token in code_tokens(path):
        yield line, token, token
        if path.suffix != ".py" and token.startswith('"'):
            try:
                value = json.loads(token)
            except ValueError:
                continue
            yield line, token, value
    if path.suffix == ".py":
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        # AST columns are UTF-8 byte offsets. Index once instead of splitting
        # a large generator's entire source again for every string constant.
        encoded = source.encode("utf-8")
        offsets = [0]
        for line in encoded.splitlines(keepends=True):
            offsets.append(offsets[-1] + len(line))
        docstrings = set()
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if isinstance(body, list) and body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                docstrings.add(body[0].value)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node not in docstrings:
                start = offsets[node.lineno - 1] + node.col_offset
                end = offsets[node.end_lineno - 1] + node.end_col_offset
                yield node.lineno, encoded[start:end].decode("utf-8"), node.value


def audit(category):
    category = category.resolve()
    registry = json.loads((category / "framework-scenarios.json").read_text())
    shared = category / "_shared"
    sources = sorted(path for folder in ("engine", "tooling", "wurst", "wurst-bootstrap")
                     for path in (shared / folder).rglob("*") if path.is_file() and path.suffix in EXTENSIONS)
    words = set().union(*(vocabulary(category / row["directory"]) for row in registry["scenarios"]))
    words.update(alias.casefold() for row in registry["scenarios"]
                 for alias in row.get("namespaceAliases", []))
    patterns = re.compile(r"(?<![a-z0-9])(?:" + "|".join(re.escape(word) for word in sorted(words, key=len, reverse=True)) + r")(?![a-z0-9])", re.I)
    exception_file = shared / "contracts/framework-boundary-exceptions.json"
    exceptions = json.loads(exception_file.read_text()) if exception_file.exists() else []
    allowed = {(row["path"], row["literal"].casefold(), row["token"]) for row in exceptions if row.get("reason")}
    errors = []
    fingerprints = {}
    for path in sources:
        relative = path.relative_to(shared).as_posix()
        for line, token, value in boundary_tokens(path):
            for match in patterns.finditer(value.casefold()):
                if (relative, match[0], token) not in allowed:
                    errors.append(f"{relative}:{line}: scenario literal {match[0]!r} belongs in content")
        for fingerprint in mechanism_fingerprints(path):
            fingerprints.setdefault(fingerprint, path)
    canonical_packages = {p.name: p for p in sources if p.suffix == ".wurst"}
    for row in registry["scenarios"]:
        project = category / row["directory"]
        excluded = {"_build", ".wurst", "__pycache__"}
        if not row["contentOnly"]:
            excluded.update(("tests", "reports"))
        for path in sorted(project.rglob("*")):
            relative = path.relative_to(project)
            if not path.is_file() or path.suffix not in EXTENSIONS or any(part in excluded for part in relative.parts):
                continue
            # A source alias must resolve to the one canonical implementation.
            if path.is_symlink() and path.resolve() in sources:
                continue
            editor_script = relative.parts[0] == "map" and path.name == "war3map.j"
            if editor_script:
                if mechanism_fingerprints(path) & fingerprints.keys():
                    errors.append(f"{row['directory']}/{relative}: copied/forked mechanism in editor script")
                continue
            if row["contentOnly"]:
                errors.append(f"{row['directory']}/{relative}: content-only campaign contains executable code")
            elif path.suffix == ".wurst" and not path.name.endswith(("Tests.wurst", "Fixture.wurst")):
                errors.append(f"{row['directory']}/{relative}: runtime implementation must be shared")
            elif path.name in canonical_packages:
                errors.append(f"{row['directory']}/{relative}: copied/forked shared package")
            elif not path.name.endswith(("Tests.wurst", "Fixture.wurst")):
                matches = mechanism_fingerprints(path) & fingerprints.keys()
                if matches:
                    original = fingerprints[next(iter(matches))].relative_to(shared)
                    errors.append(f"{row['directory']}/{relative}: copied/forked mechanism from {original}")
    return sorted(set(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("category", type=Path, nargs="?", default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    errors = audit(args.category)
    print("\n".join(errors) if errors else "OK: framework content and implementation boundary")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
