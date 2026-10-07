"""Campaign-neutral, fail-closed requirement and final-archive evidence checks.

Source/compiled references are supporting evidence, never execution receipts.
Nothing in this module promotes a parent system or a catalogue to a mechanism.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import tempfile
import zipfile
import zlib

from warcraft_campaign import MpqReader, _hash
from wurst_execution import discover, verify_evidence, WurstExecutionError

FORMAT = "warcraftmap_requirement_traceability_v1"
MARKER = re.compile(r"<!-- req:([A-Z]+-\d+) -->")
BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?")
CLASSES = {"mechanism", "content", "combination"}
CATEGORIES = ("compiled_lua", "runtime_data", "terrain", "pathing", "object_data",
              "imported_assets", "campaign_metadata", "map_metadata", "embedded_maps",
              "archive_metadata", "other")


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source_path(project, relative):
    path = (project / relative).resolve()
    # Shared engine/tooling are siblings of the scenario, not arbitrary files.
    path.relative_to(project.parent.resolve())
    if Path(relative).is_absolute() or "_build" in Path(relative).parts:
        raise ValueError("source evidence must be authoritative, relative input, not generated output")
    return path


def authority_blocks(project, paths):
    """Read every bullet AND non-heading paragraph; no untagged prose is ignored."""
    rows = []
    for relative in paths:
        current = None
        section = ""
        for number, line in enumerate(source_path(project, relative).read_text().splitlines(), 1):
            if not line.strip() or line.startswith("#") or BULLET.match(line):
                if current:
                    rows.append(current)
                    current = None
            if line.startswith("#"):
                section = line.lstrip("# ")
                continue
            if not line.strip():
                continue
            if current is None:
                current = {"path": relative, "line": number, "section": section, "text": ""}
            current["text"] += (" " if current["text"] else "") + BULLET.sub("", line).strip()
        if current:
            rows.append(current)
    for row in rows:
        matches = MARKER.findall(row["text"])
        row["id"] = matches[0] if len(matches) == 1 else None
        row["text"] = MARKER.sub("", row["text"]).strip()
    return rows


def authority_errors(project, ledger, documents=None):
    errors = []
    if not ledger.get("documents") or not ledger.get("requirements"):
        errors.append("authority documents and requirements must not be empty")
    if documents is not None and set(documents) != set(ledger["documents"]):
        errors.append("authoritative document set omitted or changed")
    blocks = authority_blocks(project, documents if documents is not None else ledger["documents"])
    by_id = {row["id"]: row for row in ledger["requirements"]}
    if len(by_id) != len(ledger["requirements"]):
        errors.append("duplicate requirement IDs")
    seen = set()
    obligations = set()
    for block in blocks:
        ident = block["id"]
        if not ident or ident in seen:
            errors.append(f"untagged/duplicate authority at {block['path']}:{block['line']}")
            continue
        seen.add(ident)
        row = by_id.get(ident)
        if (not row or row.get("text") != block["text"] or row.get("path") != block["path"]
                or row.get("section") != block["section"]):
            errors.append(f"{ident}: authority changed without requirement review")
            continue
        if row.get("classification") not in CLASSES or row.get("kind") not in {"runtime", "content", "development"}:
            errors.append(f"{ident}: missing classification/kind")
        cases = ["success", "failure", "stale", "replay"] if row.get("kind") == "runtime" else ["success", "failure"]
        if row.get("requiredCases") != cases:
            errors.append(f"{ident}: required integration cases omitted or changed")
        clauses = row.get("obligations", [])
        if not clauses or " ".join(x["text"] for x in clauses) != row["text"]:
            errors.append(f"{ident}: obligation spans omit or alter authority text")
        for clause in clauses:
            cid = clause.get("id", "")
            if not re.fullmatch(re.escape(ident) + r"\.\d+", cid) or cid in obligations:
                errors.append(f"{ident}: invalid/duplicate obligation {cid}")
            obligations.add(cid)
    errors += [f"{ident}: requirement removed from authority" for ident in sorted(set(by_id) - seen)]
    dependencies = {row["id"]: row for row in ledger.get("dependencies", [])}
    if len(dependencies) != len(ledger.get("dependencies", [])):
        errors.append("duplicate dependency IDs")
    linked = {}
    for row in ledger["requirements"]:
        for clause in row["obligations"]:
            for dependency in clause.get("dependencyIds", []):
                linked.setdefault(dependency, set()).add(clause["id"])
    for ident in set(dependencies) | set(linked):
        if set(dependencies.get(ident, {}).get("requirements", [])) != linked.get(ident, set()) or len(linked.get(ident, set())) < 2:
            errors.append(f"{ident}: dependency endpoints omitted or changed without obligation review")
    return errors


def reference_ok(project, ref):
    """Supplementary source check, including a function-scoped anchor if supplied."""
    if not isinstance(ref, dict) or not ref.get("path") or not ref.get("contains"):
        return False
    try:
        text = source_path(project, ref["path"]).read_text()
        text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
        if ref.get("symbol"):
            # Wurst's indentation scopes keep an unrelated function or comment
            # from satisfying a removed registration/persistence call.
            pattern = r"(?m)^(?P<indent>[ \t]*)(?:@test\s+)?(?:public |private |override |static )*function " + re.escape(ref["symbol"]) + r"\([^\n]*\n"
            match = re.search(pattern, text)
            if not match:
                return False
            tail = []
            for line in text[match.end():].splitlines():
                if line.strip() and len(line) - len(line.lstrip()) <= len(match["indent"]):
                    break
                tail.append(line)
            text = match[0] + "\n".join(tail)
        return all(token in text for token in ref["contains"])
    except (OSError, ValueError, TypeError):
        return False


def execution_results(project, evidence, transcript, revision):
    if evidence is None or transcript is None:
        return {}, ["current pinned Wurst execution evidence is absent"]
    try:
        verify_evidence(evidence, transcript, revision)
        # _assemble copies shared Wurst packages into the scenario's compile
        # namespace. Checking only files that still exist under project misses
        # deleted/new sources and every shared package.
        sources = {path.relative_to(project).as_posix(): path
                   for path in (project / "wurst").rglob("*.wurst")}
        for path in (project.parent / "_shared/wurst").glob("*.wurst"):
            key = "wurst/" + path.name
            if key in sources and sources[key].read_bytes() != path.read_bytes():
                raise WurstExecutionError(f"ambiguous compiled source: {key}")
            sources[key] = path
        recorded = {key for key in evidence["inputs"] if key.startswith("wurst/") and key.endswith(".wurst")}
        # ScenarioData is generated in the isolated compiler tree. It is the
        # only generated Wurst input; its packaged records have a separate census.
        if recorded - {"wurst/ScenarioData.wurst"} != set(sources) - {"wurst/ScenarioData.wurst"}:
            raise WurstExecutionError("execution Wurst source set differs from current production/test inputs")
        for key, path in sources.items():
            if evidence["inputs"].get(key) != sha(path.read_bytes()):
                raise WurstExecutionError(f"stale execution source: {key}")
        # Discovery cannot be reduced in an otherwise self-consistent evidence
        # file. Re-discover current tests, including any shared test packages.
        expected = {row["id"]: row["line"] for row in evidence["expected"]}
        current = {row["id"]: row["line"] for row in discover(project)}
        current.update({row["id"]: row["line"]
                        for row in discover(project.parent / "_shared", allow_empty=True)})
        for key, line in current.items():
            if expected.get(key) != line:
                raise WurstExecutionError(f"current test absent from execution: {key}")
        for relative in ("wurst.build", "wurst_run.args"):
            path = project / relative
            if relative in evidence["inputs"] or path.exists():
                if not path.is_file() or relative not in evidence["inputs"]:
                    raise WurstExecutionError(f"missing execution compiler settings: {relative}")
                if relative != "wurst.build" and evidence["inputs"][relative] != sha(path.read_bytes()):
                    raise WurstExecutionError(f"stale execution compiler settings: {relative}")
        for relative, digest in evidence["inputs"].items():
            # Grill install rewrites wurst.build (YAML order, document header
            # and dependency URL casing). Its executed bytes are already bound
            # by verify_evidence; build target/provenance validation owns the
            # source configuration. Never compare normalized bytes to the raw
            # source file and reject a valid pinned run as stale.
            if relative == "wurst.build":
                continue
            # Compile-only generated/library inputs are bound by the existing
            # Wurst gate. Every local production/test input must also be current.
            candidate = project / relative
            if candidate.is_file() and sha(candidate.read_bytes()) != digest:
                raise WurstExecutionError(f"stale execution source: {relative}")
        return {row["id"]: row for row in evidence["tests"]}, []
    except (WurstExecutionError, ValueError, KeyError, OSError) as error:
        return {}, [str(error)]


def test_ok(project, test, entry, results, evidence):
    if not isinstance(test, dict) or test.get("level") != "production_adapter":
        return False
    ident = test.get("id", "")
    result = results.get(ident, {})
    if result.get("status") != "pass" or test.get("entryPoint") != entry.get("id"):
        return False
    try:
        relative, symbol = ident.rsplit(":", 1)
        path = source_path(project, relative)
        # A test function's existence or a direct call to a state method is not
        # adapter execution. The reviewed mapping must invoke the real adapter
        # seam and assert the named outcome, with the exact executed source hash.
        receipt = test.get("receipt")
        registration = entry.get("registration", {}).get("symbol")
        return (isinstance(receipt, dict) and receipt in result.get("traceabilityReceipts", []) and
                receipt.get("entryPoint") == entry.get("id") and
                set(receipt.get("observed", [])) >= {"registration", "adapter", "outcome"} and
                evidence["inputs"].get(relative) == sha(path.read_bytes()) and
                bool(registration) and bool(entry.get("testInvocation")) and bool(test.get("assertions")) and
                reference_ok(project, {"path": relative, "symbol": symbol,
                                       "contains": [registration + "(", entry["testInvocation"], *test["assertions"]]}))
    except (ValueError, OSError, KeyError):
        return False


def entry_ok(project, entry, kind="runtime"):
    adapters = {"command", "event", "timer", "map-start", "transition", "combat", "ui"}
    if kind != "runtime":
        adapters.add("build")
    return (entry.get("kind") in adapters and bool(entry.get("id"))
            and bool(entry.get("registration")) and bool(entry.get("path"))
            and all(reference_ok(project, ref) for ref in [entry["registration"], *entry["path"]]))


def _zip_container(path):
    # is_zipfile alone also recognizes a ZIP embedded at the end of a W3N.
    # Select the outer format first; never census the last nested map instead.
    with path.open("rb") as stream:
        signature = stream.read(4)
    return signature.startswith(b"PK") and zipfile.is_zipfile(path)


def _members(path):
    try:
        if _zip_container(path):
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if len(names) != len({name.replace("\\", "/").casefold() for name in names}):
                    raise ValueError("duplicate archive members")
                return {name.replace("\\", "/").casefold(): archive.read(name) for name in names if not name.endswith("/")}
        return MpqReader(path).members()
    except (zipfile.BadZipFile, struct.error, zlib.error, IndexError) as error:
        raise ValueError(f"unreadable final archive: {error}") from error


def category(name):
    name = name.lower().replace("\\", "/")
    if name.endswith(".w3x"):
        return "embedded_maps"
    if name.endswith(".lua"):
        return "compiled_lua"
    if name.startswith("runtime/"):
        return "runtime_data"
    if name.endswith(".w3e"):
        return "terrain"
    if name.endswith(".wpm"):
        return "pathing"
    if name.endswith((".doo", ".w3u", ".w3t", ".w3a", ".w3b", ".w3d", ".w3h", ".w3q")):
        return "object_data"
    if name in {"war3campaign.w3f", "campaign-manifest.json"}:
        return "campaign_metadata"
    if name.startswith("("):
        return "archive_metadata"
    if name.startswith("war3map."):
        return "map_metadata"
    if name.startswith(("war3mapimported/", "assets/", "imports/")) or name.endswith((".blp", ".dds", ".tga", ".mdx", ".mdl", ".wav", ".mp3", ".ogg")):
        return "imported_assets"
    return "other"


def stored_sizes(path, members):
    if _zip_container(path):
        with zipfile.ZipFile(path) as archive:
            return {row.filename.replace("\\", "/").casefold(): row.compress_size for row in archive.infolist()}
    reader = MpqReader(path)
    by_hash = {(one, two): block for one, two, _, _, block in reader.hashes}
    return {name: reader.blocks[by_hash[(_hash(name, 1), _hash(name, 2))]][1] for name in members}


def composition(members, size, stored):
    totals = dict.fromkeys(CATEGORIES, 0)
    packed_totals = dict.fromkeys(CATEGORIES, 0)
    rows = []
    for name, payload in sorted(members.items()):
        kind = category(name)
        totals[kind] += len(payload)
        packed_totals[kind] += stored[name]
        rows.append({"path": name, "category": kind, "decodedBytes": len(payload), "storedBytes": stored[name], "sha256": sha(payload)})
    overhead = size - sum(packed_totals.values())
    if overhead < 0:
        raise ValueError("archive member storage overlaps or exceeds the final archive")
    return {"archiveBytes": size, "decodedBytes": sum(totals.values()), "categories": totals,
            "storedCategories": packed_totals, "containerOverheadBytes": overhead, "members": rows}


def inspect_artifact(path, maps):
    """Read the final W3N and its embedded W3X bytes, never build directories."""
    campaign = _members(path)
    expected = {row["packagePath"].casefold() for row in maps}
    actual = {name for name in campaign if name.lower().endswith(".w3x")}
    errors = []
    if not maps or len(expected) != len(maps) or len({row["id"] for row in maps}) != len(maps):
        errors.append("physical map manifest is empty or has duplicate IDs/paths")
    if actual != expected:
        errors.append(f"embedded map set differs: missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")
    result = {"sha256": sha(path.read_bytes()), "composition": composition(campaign, path.stat().st_size, stored_sizes(path, campaign)), "maps": []}
    payloads = {}
    inspected_maps = list(maps) + [{"id": "@unexpected/" + name, "packagePath": name, "unexpected": True}
                                  for name in sorted(actual - expected)]
    for row in inspected_maps:
        try:
            payload = campaign[row["packagePath"].casefold()]
            with tempfile.NamedTemporaryFile(suffix=".w3x") as nested:
                nested.write(payload)
                nested.flush()
                members = _members(Path(nested.name))
                stored = stored_sizes(Path(nested.name), members)
            # Keep byte accounting even if runtime identity/JSON/Lua is broken.
            result["maps"].append({"id": row["id"], "sha256": sha(payload), **composition(members, len(payload), stored)})
            if row.get("unexpected"):
                continue
            runtime = json.loads(members["runtime/scenario-runtime.json"])
            if not isinstance(runtime, dict) or not isinstance(runtime.get("physicalMap"), dict):
                raise ValueError("runtime payload/physical map must be an object")
            physical = runtime.get("physicalMap", {})
            if physical.get("id") != row["id"] or physical.get("bootstrap") != row["bootstrap"]:
                raise ValueError("runtime physical map identity differs from source")
            script = members["war3map.lua"].decode("utf-8")
            payloads[row["id"]] = {"runtime": runtime, "script": script, "members": members}
        except (KeyError, ValueError, OSError, zipfile.BadZipFile) as error:
            errors.append(f"{row['id']}: artifact-missing: {error}")
    # The outer embedded_maps bytes include compression/container overhead.
    # Nested decoded categories are a separate view and must not be added to it.
    result["nestedDecodedCategories"] = {key: sum(row["categories"][key] for row in result["maps"]) for key in CATEGORIES}
    result["nestedStoredCategories"] = {key: sum(row["storedCategories"][key] for row in result["maps"]) for key in CATEGORIES}
    result["nestedContainerOverheadBytes"] = sum(row["containerOverheadBytes"] for row in result["maps"])
    result["accounting"] = "Outer and nested views are separate. Stored categories plus container overhead equal archive bytes; decoded categories expose compression. Size is not a correctness gate."
    return result, payloads, errors


def select(data, selector):
    values = [data]
    for key in selector.split("."):
        following = []
        for value in values:
            if key == "*":
                following.extend(value.values() if isinstance(value, dict) else value)
            elif isinstance(value, dict) and key in value:
                following.append(value[key])
            else:
                raise ValueError(f"missing catalogue selector {selector}")
        values = following
    return [row for value in values for row in (value if isinstance(value, list) else [value])]


def records(data, spec):
    rows = select(data, spec["selector"])
    if spec.get("idKey") == "@key":
        if len(rows) != 1 or not isinstance(rows[0], dict) or any(not key for key in rows[0]):
            raise ValueError("keyed catalogue must be a single object with nonempty IDs")
        return rows[0]
    if spec.get("exclude"):
        rows = [row for row in rows if not all(row.get(k) == v for k, v in spec["exclude"].items())]
    identities = [row if isinstance(row, str) else row[spec.get("idKey", "id")] for row in rows]
    if any(not isinstance(ident, str) or not ident for ident in identities) or len(identities) != len(set(identities)):
        raise ValueError("empty or duplicate catalogue IDs")
    return dict(zip(identities, rows))


def census(project, specs, maps, payloads):
    reports, errors = [], []
    for spec in specs:
        ident = spec["id"]
        row = {"id": ident, "sources": spec["sources"], "sourceHashes": {}, "maps": [], "failures": []}
        expected = {}
        try:
            if spec.get("compare") not in {"ids", "records"} or spec.get("distribution", "replicated") not in {"replicated", "union"}:
                raise ValueError("unrecognized catalogue comparison/distribution policy")
            if not spec.get("sources") or not spec.get("runtime"):
                raise ValueError("catalogue source and packaged selectors are required")
            for source in spec["sources"]:
                raw = source_path(project, source["path"]).read_bytes()
                row["sourceHashes"][source["path"]] = sha(raw)
                entries = records(json.loads(raw), source)
                if set(entries) & set(expected):
                    raise ValueError("duplicate IDs between authoritative catalogues")
                expected.update(entries)
            row["sourceCount"] = len(expected)
            row["sourceIdsSha256"] = sha(canonical(sorted(expected)))
            # Some generated constructors serve more than one catalogue (for
            # example technologies and institutions). Enumerate the other
            # authoritative IDs explicitly instead of accepting arbitrary extras.
            companions = set()
            for source in spec.get("compiledCompanions", []):
                raw = source_path(project, source["path"]).read_bytes()
                row["sourceHashes"][source["path"]] = sha(raw)
                companions.update(source.get("idPrefix", "") + key + source.get("idSuffix", "")
                                  for key in records(json.loads(raw), source))
            if not payloads:
                row["packagedUniqueCount"] = None
                row["failures"].append("final runtime payload not inspected")
                row["status"] = "fail"
                reports.append(row)
                errors.append(f"{ident}: final runtime payload not inspected")
                continue
            union = set()
            for physical in maps:
                if physical["bootstrap"]:
                    continue
                wanted = expected
                partition = spec.get("partition")
                if partition:
                    wanted = {key: value for key, value in expected.items()
                              if value[partition["sourceField"]] in physical[partition["mapField"]]}
                payload = payloads.get(physical["id"], {})
                patterns = spec.get("compiledIdPatterns", [spec["compiledIdPattern"]] if spec.get("compiledIdPattern") else [])
                compiled_ids = set()
                for pattern in patterns:
                    matcher = re.compile(pattern.replace("{id}", r'(?P<identity>"(?:\\.|[^"\\])*")'))
                    compiled_ids.update(json.loads(match["identity"]) for statement in compiled_fragments(payload)
                                        if (match := matcher.match(statement)) and json.loads(match["identity"]))
                try:
                    if spec["runtime"].get("representation") == "compiled-identities":
                        if spec["compare"] != "ids" or not patterns:
                            raise ValueError("compiled identity census requires ID comparison and explicit patterns")
                        found = {key: key for key in compiled_ids}
                    else:
                        found = records(payload.get("runtime", {}), spec["runtime"])
                except (ValueError, KeyError, TypeError) as error:
                    found = {}
                    row["failures"].append(f"{physical['id']}: {error}")
                union.update(found)
                if spec.get("distribution") == "union":
                    wanted = {key: value for key, value in wanted.items() if key in found}
                missing, extra = sorted(set(wanted)-set(found)), sorted(set(found)-set(wanted))
                changed = []
                if spec.get("compare") == "records":
                    changed = sorted(key for key in set(wanted) & set(found) if wanted[key] != found[key])
                # This only checks compilation survival. It never establishes
                # runtime reachability; each requirement needs executed adapters.
                compiled_missing = []
                compiled_extra = []
                compiled_count = None
                if patterns:
                    compiled_count = len(compiled_ids)
                    compiled_missing = sorted(set(wanted) - compiled_ids)
                    # A local JSON projection may coexist with global compiled
                    # authority for inactive-region simulation. Only identities
                    # outside the authoritative source universe are unexpected.
                    compiled_extra = sorted(compiled_ids - set(expected) - companions)
                else:
                    row["failures"].append(f"{physical['id']}: compiled catalogue registration mapping absent")
                if missing or extra or changed or compiled_missing or compiled_extra:
                    row["failures"].append(f"{physical['id']}: source-to-artifact mismatch")
                row["maps"].append({"id": physical["id"], "expectedCount": len(wanted), "packagedCount": len(found),
                                    "missingIds": missing, "unexpectedIds": extra, "changedIds": changed,
                                    "compiledCount": compiled_count, "compiledMissingIds": compiled_missing,
                                    "compiledUnexpectedIds": compiled_extra})
            row["packagedUniqueCount"] = len(union)
            if union != set(expected):
                row["failures"].append("campaign-wide catalogue identity/count mismatch")
        except (ValueError, KeyError, OSError, TypeError, re.error) as error:
            row["failures"].append(str(error))
        row["status"] = "fail" if row["failures"] else "pass"
        reports.append(row)
        errors.extend(f"{ident}: {error}" for error in row["failures"])
    return reports, errors


def lua_code_mask(script):
    ignored = re.compile(r'--\[(=*)\[.*?\]\1\]|--[^\n]*|\[(=*)\[.*?\]\2\]|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)
    return ignored.sub(lambda match: re.sub(r"[^\n]", " ", match[0]), script)


def lua_calls(script):
    """Return actual call expressions, excluding declarations, strings and comments.

    This is compilation-survival evidence only, not a Lua control-flow proof.
    Quoted/long-bracket diagnostic markers cannot impersonate registrations.
    """
    code = lua_code_mask(script)
    expressions = []
    for match in re.finditer(r"[\w.:]+\s*\(", code):
        if re.search(r"\bfunction\s*$", code[max(0, match.start()-20):match.start()]):
            continue
        depth = 1
        end = match.end()
        while end < len(code) and depth:
            depth += (code[end] == "(") - (code[end] == ")")
            end += 1
        if not depth:
            expressions.append(script[match.start():end])
    return expressions


def compiled_calls(payload):
    if "calls" not in payload:
        payload["calls"] = lua_calls(payload.get("script", ""))
    return payload["calls"]


def compiled_fragments(payload):
    """Calls and real assignments, including identities in inlined constructors.

    Quoted diagnostics/comments are masked before locating assignment targets.
    This describes bytes that survived optimization, not execution/reachability.
    """
    if "fragments" not in payload:
        script = payload.get("script", "")
        code = lua_code_mask(script)
        assignments = []
        for match in re.finditer(r"\b[\w.]+\[[^\]\n]+\]\s*=(?!=)", code):
            end = script.find("\n", match.end())
            assignments.append(script[match.start():end if end >= 0 else len(script)])
        payload["fragments"] = compiled_calls(payload) + assignments
    return payload["fragments"]


def artifact_ok(mapping, maps, payloads):
    artifact = mapping.get("artifact", {})
    ids = artifact.get("mapIds", [])
    if ids == ["@regional"]:
        ids = [row["id"] for row in maps if not row["bootstrap"]]
    if not ids or not artifact.get("callPatterns"):
        return False
    for ident in ids:
        if ident not in payloads:
            return False
        calls = compiled_calls(payloads[ident])
        if not all(any(re.match(pattern, call) for call in calls) for pattern in artifact["callPatterns"]):
            return False
    return True


def audit(project, ledger, mappings, catalogue_specs, maps, *, artifact=None,
          evidence=None, transcript=None, revision="", authority_documents=None):
    blockers = []
    def block(ident, code, message):
        blockers.append({"id": ident, "class": code, "message": message})
    for message in authority_errors(project, ledger, authority_documents):
        block("authority", "authority-drift", message)
    results, execution_errors = execution_results(project, evidence, transcript, revision)
    if results:
        # Receipts must have been emitted inside the named successful test,
        # not merely inserted into a JSON evidence file or another test's log.
        runs = list(re.finditer(r"^Running (.+\.wurst):(\d+) - (\w+)\.\.\s*$", transcript.decode(), re.M))
        log = transcript.decode()
        results = {key: dict(value) for key, value in results.items()}
        for index, run in enumerate(runs):
            matching = [key for key in results if key.endswith(":"+run[3]) and run[1].endswith(key.rsplit(":", 1)[0])]
            if len(matching) != 1:
                continue
            body = log[run.end():runs[index+1].start() if index+1 < len(runs) else len(log)]
            # A receipt after the terminal test result (including after suite
            # completion) was not observed during this test's execution.
            terminal = re.search(r"^\s*OK!\s*$", body, re.M)
            body = body[:terminal.start()] if terminal else ""
            receipts = []
            for encoded in re.findall(r"^\s*TRACEABILITY (\{[^\n]+\})\s*$", body, re.M):
                try:
                    receipts.append(json.loads(encoded))
                except ValueError:
                    pass
            results[matching[0]]["traceabilityReceipts"] = receipts
    artifact_report, payloads = None, {}
    if artifact:
        try:
            artifact_report, payloads, errors = inspect_artifact(artifact, maps)
            for error in errors:
                block("artifact", "artifact-missing", error)
        except (ValueError, OSError, KeyError, zipfile.BadZipFile) as error:
            block("artifact", "artifact-missing", str(error))
    else:
        block("artifact", "artifact-missing", "exact final W3N has not been supplied")
    requirements = []
    by_id = mappings.get("requirements", {})
    leaf_ids = {clause["id"] for row in ledger["requirements"] for clause in row["obligations"]}
    for ident in sorted(set(by_id)-leaf_ids):
        block(ident, "invalid-mapping", "mapping must name an individual obligation, never a parent system or wildcard")
    for parent in ledger["requirements"]:
        for clause in parent["obligations"]:
            ident = clause["id"]
            mapping = by_id.get(ident, {})
            before = len(blockers)
            if not mapping:
                block(ident, "unmapped", "no explicit requirement-to-production mapping")
            content = mapping.get("content", [])
            mechanism = mapping.get("mechanism", [])
            if parent["classification"] in {"content", "combination"} and (not content or not all(reference_ok(project, ref) for ref in content)):
                block(ident, "authority-missing", "scenario content authority is absent or stale")
            mechanism_valid = bool(mechanism) and all(
                Path(ref.get("path", "")).suffix in {".wurst", ".py", ".lua"}
                and "test" not in Path(ref.get("path", "")).stem.lower()
                and reference_ok(project, ref) for ref in mechanism)
            if parent["classification"] in {"mechanism", "combination"} and not mechanism_valid:
                block(ident, "data-only" if content else "mechanism-missing", "reusable mechanism evidence is absent or stale")
            entry = mapping.get("entry", {})
            entry_valid = entry_ok(project, entry, parent["kind"])
            if not entry_valid:
                block(ident, "unreachable", "production entry/registration/call chain is absent or stale")
            state = mapping.get("state", {})
            if (not all(state.get(key) for key in ("owner", "mutation", "rejection", "outcome"))
                    or not state.get("references") or not all(reference_ok(project, ref) for ref in state["references"])):
                block(ident, "state-unmapped", "owner, mutation, rejection and player-visible outcome must be explicit")
            for field in ("persistence", "transition"):
                policy = mapping.get(field, {})
                if (policy.get("mode") not in {"persisted", "reconstructed", "session-only", "read-only", "build-only"}
                        or not policy.get("reason") or not policy.get("references")
                        or not all(reference_ok(project, ref) for ref in policy["references"])
                        or (parent["kind"] == "runtime" and policy.get("mode") == "build-only")
                        or (policy.get("mode") == "persisted" and
                            not all(reference_ok(project, policy.get(path)) for path in ("save", "load")))):
                    block(ident, "unpersisted", f"{field} behavior/path is absent or stale")
            tests = mapping.get("tests", {})
            cases = parent["requiredCases"]
            for case in cases:
                receipt = tests.get(case, {}).get("receipt", {})
                observed = {"registration", "adapter", "validation", "mutation", "outcome"}
                observed.update(field for field in ("persistence", "transition")
                                if mapping.get(field, {}).get("mode") in {"persisted", "reconstructed"})
                if (receipt.get("requirement") != ident or receipt.get("case") != case or
                        not observed <= set(receipt.get("observed", [])) or
                        not test_ok(project, tests.get(case), entry, results, evidence)):
                    block(ident, "test-only" if tests.get(case, {}).get("level") == "internal" else "integration-missing",
                          f"{case}: current executable production-adapter evidence is absent")
            if mapping and not any(test_ok(project, test, entry, results, evidence) for test in tests.values()):
                block(ident, "static-only", "source references cannot establish executed integration")
            if not artifact_ok(mapping, maps, payloads):
                block(ident, "artifact-missing", "compiled implementation/registration evidence is absent")
            requirements.append({"id": ident, "parent": parent["id"], "text": clause["text"],
                                 "classification": parent["classification"], "kind": parent["kind"],
                                 "authority": {"path": parent["path"], "section": parent["section"]},
                                 "mapping": mapping, "blockerClasses": sorted({row["class"] for row in blockers[before:]}),
                                 "status": "fail" if len(blockers) > before else "pass"})
    dependencies = []
    dependency_ids = {row["id"] for row in ledger.get("dependencies", [])}
    for ident in sorted(set(mappings.get("dependencies", {})) - dependency_ids):
        block(ident, "invalid-mapping", "dependency mapping names an unknown interaction")
    for dependency in ledger.get("dependencies", []):
        ident = dependency["id"]
        mapping = mappings.get("dependencies", {}).get(ident, {})
        entry = mapping.get("entry", {})
        tests = mapping.get("tests", {})
        endpoints = dependency["requirements"]
        covered = (len(endpoints) >= 2 and set(endpoints) <= leaf_ids and mapping.get("requirements") == endpoints
                   and entry_ok(project, entry)
                   and all(tests.get(case, {}).get("receipt", {}).get("requirement") == ident
                           and tests.get(case, {}).get("receipt", {}).get("case") == case
                           and {"validation", "mutation"} <= set(tests.get(case, {}).get("receipt", {}).get("observed", []))
                           and test_ok(project, tests.get(case), entry, results, evidence) for case in ("success", "failure", "replay"))
                   and all(any(row["id"] == endpoint and row["status"] == "pass" for row in requirements) for endpoint in endpoints))
        if not covered:
            block(ident, "dependency-uncovered", dependency["interaction"])
        dependencies.append({**dependency, "mapping": mapping, "status": "pass" if covered else "fail"})
    expected_catalogues = set(ledger["requiredCatalogues"])
    actual_catalogues = [row["id"] for row in catalogue_specs]
    if set(actual_catalogues) != expected_catalogues or len(set(actual_catalogues)) != len(actual_catalogues):
        block("catalogues", "census-mismatch", "required catalogue census omitted, duplicated or unexpected")
    catalogue_report, errors = census(project, catalogue_specs, maps, payloads)
    for message in errors:
        block("catalogues", "census-mismatch", message)
    return {"format": FORMAT, "status": "fail" if blockers else "pass", "candidateReady": not blockers,
            "requirements": requirements, "dependencies": dependencies, "catalogues": catalogue_report,
            "artifact": artifact_report, "executionErrors": execution_errors,
            "authorityHashes": {path: sha(source_path(project, path).read_bytes())
                                for path in (authority_documents if authority_documents is not None else ledger["documents"])},
            "ledgerSha256": sha(canonical(ledger)), "mappingSha256": sha(canonical(mappings)),
            "censusSpecSha256": sha(canonical(catalogue_specs)),
            "blockerCount": len(blockers), "blockerClasses": dict(sorted(Counter(row["class"] for row in blockers).items())),
            "blockers": blockers}


def require_ready(report):
    if report.get("status") != "pass" or report.get("candidateReady") is not True or report.get("blockers") or report.get("blockerCount") != 0:
        raise ValueError(f"requirement traceability blocks candidate publication: {report.get('blockerCount', 'unknown')} blockers")


def render_markdown(report):
    lines = ["# Requirement-to-production traceability", "", f"Candidate ready: **{report['candidateReady']}**; blockers: **{report['blockerCount']}**.", "",
             "Each row is an individual obligation. Source and compiled markers are supplementary evidence; internal-method tests and broad system presence cannot satisfy production integration.", "",
             "| Requirement | Classification | Authority | Blockers |", "|---|---|---|---|"]
    for row in report["requirements"]:
        lines.append(f"| {row['id']} | {row['classification']} | {row['text'].replace('|', '/')} | {', '.join(row['blockerClasses']) or 'none'} |")
    lines += ["", "## Cross-system dependencies", ""]
    lines += [f"- {row['id']}: {row['interaction']} — {row['status']} ({', '.join(row['requirements'])})" for row in report["dependencies"]]
    lines += ["", "## Packaged content census", "", "Counts are unique stable IDs; per-map assignments, missing/extra/changed IDs and compiled survival are detailed in JSON.", "",
              "| Catalogue | Source | Packaged union | Status |", "|---|---:|---:|---|"]
    lines += [f"| {row['id']} | {row.get('sourceCount', '?')} | {row.get('packagedUniqueCount', '?')} | {row['status']} |" for row in report["catalogues"]]
    lines += ["", "## Final artifact byte composition", ""]
    if report["artifact"]:
        artifact = report["artifact"]
        lines += [f"W3N SHA-256: `{artifact['sha256']}`", "", artifact["accounting"], "",
                  "| Category | Outer stored | Outer decoded | Nested stored | Nested decoded |", "|---|---:|---:|---:|---:|"]
        lines += [f"| {key} | {artifact['composition']['storedCategories'][key]} | {artifact['composition']['categories'][key]} | {artifact['nestedStoredCategories'][key]} | {artifact['nestedDecodedCategories'][key]} |" for key in CATEGORIES]
        lines += ["", f"Final archive: {artifact['composition']['archiveBytes']} bytes. Container overhead: {artifact['composition']['containerOverheadBytes']} outer bytes, {artifact['nestedContainerOverheadBytes']} nested bytes."]
    else:
        lines += ["No final W3N supplied. Byte composition and packaged evidence are unavailable; publication is blocked."]
    lines += ["", "## Blockers", ""]
    lines += [f"- {row['id']} [{row['class']}]: {row['message']}" for row in report["blockers"]]
    return "\n".join(lines) + "\n"
