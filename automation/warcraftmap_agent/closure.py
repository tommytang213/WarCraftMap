"""Fail-closed planning policy over freshly regenerated scenario audits.

Stable blocker identities survive wording changes, issue renames and PR merges.
A merge is history, not closure: only a new audit on current main removes work.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
import re
from typing import Any


REPORTS = {
    "release": "reports/release-blocker-audit.json",
    "runtime": "reports/runtime-acceptance.json",
    "traceability": "reports/traceability/requirements.json",
}
MARKER = re.compile(r"(?m)^Closure blocker: ([\w.:-]+)\s*$")
REVISION = re.compile(r"(?m)^Closure revision: ([0-9a-f]{40})\s*$")
# Narrow owner-approved exception: issue #427 is CI-worker maintenance, not
# a gameplay/release blocker. It may enter the normal worker only after #426
# was MERGED (not merely closed), with the usual checks and budgets unchanged.
APPROVED_MAINTENANCE_MERGED_PR = {427: 426}


def marked_keys(entry: dict) -> set[str]:
    return set(MARKER.findall(entry.get("body") or ""))


def is_open(entry: dict) -> bool:
    return str(entry.get("state", "OPEN")).upper() == "OPEN"


@dataclass
class Blocker:
    key: str
    title: str
    messages: list[str] = field(default_factory=list)
    reports: list[str] = field(default_factory=list)
    dependencies: set[str] = field(default_factory=set)


def report_blockers(name: str, report: dict) -> dict[str, Blocker]:
    """Group repeated symptoms for one obligation; retain all evidence messages."""
    result: dict[str, Blocker] = {}

    def add(key, title, message, dependencies=()):
        row = result.setdefault(key, Blocker(key, title))
        if message not in row.messages:
            row.messages.append(message)
        if REPORTS[name] not in row.reports:
            row.reports.append(REPORTS[name])
        row.dependencies.update(dependencies)

    if name == "traceability":
        requirements = {row["id"]: row for row in report["requirements"]}
        dependencies = {row["id"]: row for row in report["dependencies"]}
        for finding in report["blockers"]:
            ident = finding["id"]
            source = requirements.get(ident, dependencies.get(ident, {}))
            title = source.get("text", source.get("interaction", ident))
            parents = ["traceability:" + key for key in source.get("requirements", [])]
            parents += ["traceability:" + key for key in source.get("dependsOn", [])]
            add("traceability:" + ident, title,
                f"{finding['class']}: {finding['message']}", parents)
        clean = report["blockerCount"] == 0 and not report["blockers"]
        if "traceability:artifact" in result and "traceability:catalogues" in result:
            # The package census cannot validate payloads until an exact final
            # artifact exists. Source/mapping repairs remain independent.
            result["traceability:catalogues"].dependencies.add("traceability:artifact")
        if report["blockerCount"] != len(report["blockers"]):
            add("audit:traceability", "Repair inconsistent traceability audit", "Blocker count does not match findings")
    elif name == "release":
        taxonomy = {row["id"]: row["releaseBlocking"] for row in report["taxonomy"]}
        for finding in report["findings"]:
            # Unknown severity/disposition cannot silently exempt a finding.
            if finding.get("disposition") == "resolved" or taxonomy.get(finding.get("severity"), True) is False:
                continue
            ident = finding["id"]
            key = "release:" + ident
            if ident.startswith("RUNTIME-MISSING-"):
                key = "runtime:" + ident.removeprefix("RUNTIME-MISSING-").lower().replace("-", "_")
            elif ident == "RUNTIME-EVIDENCE-INCOMPLETE":
                key = "runtime:evidence"
            add(key, ident, finding["message"], finding.get("dependsOn", []))
        clean = report["unresolvedCampaignBlockers"] == 0 and not result
    else:
        for row in report["systems"]:
            if row["releaseRequired"] and (row.get("executionStatus") != "completed" or
                    any(row["stages"].get(stage) is not True for stage in
                        ("runtimeIntegrated", "playerFacingComplete", "releaseValidated"))):
                add("runtime:" + row["id"], f"Complete {row['id']} production integration",
                    "; ".join(row.get("diagnostics", [])) or "Same-revision executed integration and built-artifact verification are required",
                    row.get("dependsOn", []))
        for failure in report["failures"]:
            add("runtime:evidence", "Regenerate and repair runtime execution/artifact evidence", failure)
        if "runtime:evidence" in result and report.get("executionStatus") != "completed":
            for row in report["systems"]:
                key = "runtime:" + row["id"]
                checks = row.get("sourceChecks", {})
                readiness = [checks.get(stage) for stage in
                             ("dataComplete", "runtimeIntegrated", "playerFacingComplete")]
                if key not in result:
                    continue
                if all(value is True for value in readiness):
                    # Missing global execution is not twenty independent
                    # implementation failures. Re-audit after evidence exists.
                    result[key].dependencies.add("runtime:evidence")
                elif any(value is False for value in readiness):
                    result["runtime:evidence"].dependencies.add(key)
        clean = not report["failures"] and not result
    if not clean or report.get("status") != "pass" or report.get("candidateReady") is not True:
        if not result:
            add("audit:" + name, f"Repair {name} audit", "Audit is not a zero-blocker passing report")
    return result


@dataclass
class Closure:
    revision: str
    fresh: bool
    blockers: dict[str, Blocker]
    issues: list[dict] = field(default_factory=list)
    prs: list[dict] = field(default_factory=list)
    reports: dict[str, Any] = field(default_factory=dict)

    def keys_for(self, entry: dict) -> set[str]:
        keys = marked_keys(entry)
        if keys:
            # Machine ownership is exact. Mentioning a prerequisite in prose
            # must not turn dependent work into its own prerequisite repair.
            return keys
        if re.match(r"^\[planned\]\s+", entry.get("title") or "", re.IGNORECASE):
            # A release reservation may cite the obligations it is waiting for.
            # Treating those citations as ownership would prevent their repairs
            # from being planned while the reservation itself cannot promote.
            return set()
        text = (entry.get("title") or "") + "\n" + (entry.get("body") or "")
        # Also recognize pre-controller issues/PRs citing stable audit IDs.
        for ident in re.findall(r"\b(?:REQ|ROAD|DEP|RUNTIME|REPORT|CONTENT|INPUT)-[\w.-]+\b", text):
            candidates = {"traceability:" + ident, "release:" + ident}
            if ident.startswith("RUNTIME-MISSING-"):
                candidates.add("runtime:" + ident.removeprefix("RUNTIME-MISSING-").lower().replace("-", "_"))
            if ident == "RUNTIME-EVIDENCE-INCOMPLETE":
                candidates.add("runtime:evidence")
            keys.update(candidates & self.blockers.keys())
        return keys

    @cached_property
    def _owners(self) -> dict[str, list[dict]]:
        result: dict[str, list[dict]] = {}
        issues = {row["number"]: self.keys_for(row) for row in self.issues}
        for row in self.issues:
            for key in issues[row["number"]]:
                result.setdefault(key, []).append(row)
        for row in self.prs:
            keys = self.keys_for(row)
            for ref in row.get("closingIssuesReferences", []):
                keys.update(issues.get(ref["number"], set()))
            for key in keys:
                result.setdefault(key, []).append(row)
        return result

    def owners(self, key: str) -> list[dict]:
        return self._owners.get(key, [])

    @cached_property
    def open_repairs(self) -> list[dict]:
        owned = {id(row) for owners in self._owners.values() for row in owners}
        return [row for row in [*self.issues, *self.prs] if is_open(row) and
                id(row) in owned]

    @property
    def active(self) -> bool:
        return not self.fresh or bool(self.blockers or self.open_repairs)

    def needs_plan(self, key: str) -> bool:
        owners = self.owners(key)
        if any(is_open(row) for row in owners):
            return False
        # Closed work is never proof of success. A fresh failing audit on a new
        # main revision allows one follow-up, while same-revision retries dedup.
        audited = {row["path"] for row in self.reports.values() if row.get("regenerated")}
        finding_fresh = key.startswith("audit:") or set(self.blockers[key].reports) <= audited
        if owners and (not self.fresh or not finding_fresh or any(
                self.revision in REVISION.findall(row.get("body") or "") for row in owners)):
            return False
        return True

    def dependency_pending(self, key: str) -> bool:
        if key in self.blockers or any(is_open(row) for row in self.owners(key)):
            return True
        # Absence from an unreadable/stale report is not prerequisite closure.
        report = key.split(":", 1)[0]
        return not self.fresh or self.reports.get(report, {}).get("regenerated") is not True

    @cached_property
    def actionable(self) -> list[str]:
        return [key for key, row in sorted(self.blockers.items())
                if not any(self.dependency_pending(dep) for dep in row.dependencies) and self.needs_plan(key)]

    def permits_issue(self, issue: dict) -> bool:
        if not self.active:
            return True
        # Explicit, reviewed CI maintenance may proceed while release closure
        # is pending, but only after its prerequisite PR is actually merged.
        # Keep stale/unregenerated audit checkouts fail-closed.
        prerequisite = APPROVED_MAINTENANCE_MERGED_PR.get(issue.get("number"))
        if (self.fresh and prerequisite is not None
                and re.match(r"^\[agent-ready\]\s+", issue.get("title") or "", re.IGNORECASE)
                and any(row.get("number") == prerequisite
                        and str(row.get("state") or "").upper() == "MERGED"
                        and row.get("mergedAt") for row in self.prs)):
            return True
        keys = self.keys_for(issue)
        if not keys:
            return False
        return all(not any(self.dependency_pending(dep) for dep in self.blockers[key].dependencies - keys)
                   for key in keys if key in self.blockers)

    def planning_view(self, limit: int = 10) -> dict:
        candidates = self.actionable[:limit]
        return {
            "revision": self.revision, "fresh": self.fresh, "active": self.active,
            "blockerCount": len(self.blockers), "reports": self.reports,
            "openRepairs": [{"number": row["number"], "title": row["title"]} for row in self.open_repairs],
            "actionableCount": len(self.actionable),
            "candidates": [{"key": key, "title": self.blockers[key].title,
                            "messages": self.blockers[key].messages,
                            "reports": self.blockers[key].reports,
                            "dependencies": sorted(self.blockers[key].dependencies),
                            "previousWork": [{"number": row["number"], "state": row.get("state")}
                                             for row in self.owners(key)]} for key in candidates],
        }


def build_closure(bundle: dict, revision: str, issues=(), prs=(), *, checkout_current=True) -> Closure:
    if not isinstance(bundle, dict):
        bundle = {}
    fresh = (checkout_current and bool(re.fullmatch(r"[0-9a-f]{40}", revision)) and
             bundle.get("revision") == revision and bundle.get("regenerated") is True)
    blockers: dict[str, Blocker] = {}
    summaries = {}
    reports = bundle.get("reports")
    reports = reports if isinstance(reports, dict) else {}
    for name, path in REPORTS.items():
        saved = reports.get(name, {})
        saved = saved if isinstance(saved, dict) else {}
        report = saved.get("report") if fresh and not saved.get("error") else saved.get("recorded")
        error = saved.get("error", "")
        try:
            if not isinstance(report, dict):
                raise ValueError("report missing")
            found = report_blockers(name, report)
            if fresh and (report.get("sourceRevision") not in (None, revision) or
                          (name in {"release", "runtime"} and report.get("candidateReady") is True and
                           report.get("sourceRevision") != revision)):
                error = "Report execution evidence belongs to a stale or missing source revision"
            for key, row in found.items():
                previous = blockers.setdefault(key, row)
                if previous is not row:
                    previous.messages = list(dict.fromkeys([*previous.messages, *row.messages]))
                    previous.reports = list(dict.fromkeys([*previous.reports, *row.reports]))
                    previous.dependencies.update(row.dependencies)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            error = f"cannot read {path}: {exc}"
        if not fresh or error:
            key = "audit:" + name
            blockers[key] = Blocker(key, f"Regenerate {name} audit on current main",
                                    [error or "Audit revision is stale or regeneration is missing"], [path])
        summaries[name] = {"path": path, "status": report.get("status") if isinstance(report, dict) else "missing",
                           "regenerated": fresh and not bool(error), "error": error}
    return Closure(revision, fresh, blockers, list(issues), list(prs), summaries)
