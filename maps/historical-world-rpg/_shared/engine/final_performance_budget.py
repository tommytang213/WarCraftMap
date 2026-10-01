"""Scenario-neutral validation and comparison of versioned performance budgets."""
from __future__ import annotations

import json, math
from pathlib import Path

FORMAT = "warcraftmap_final_performance_budgets_v1"
REPORT_FORMAT = "warcraftmap_final_performance_report_v1"
CLASSES = {"timing", "deterministic_size"}
UNITS_BY_CLASS = {
    "timing": {"ms"},
    "deterministic_size": {"bytes", "channels", "objects", "orders", "queries"},
}

class BudgetConfigurationError(ValueError): pass

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)

def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("format") != FORMAT: raise BudgetConfigurationError("unsupported final-budget format")
    if not isinstance(data.get("budgetVersion"), int) or data["budgetVersion"] < 1: raise BudgetConfigurationError("budgetVersion must be positive")
    workloads = data.get("workloads", {})
    if not workloads: raise BudgetConfigurationError("workloads are required")
    seen = set()
    for wid, workload in workloads.items():
        if not isinstance(wid, str) or not wid: raise BudgetConfigurationError("workload ids must be non-empty strings")
        if not isinstance(workload.get("version"), int) or workload["version"] < 1 or not isinstance(workload.get("source"), str) or not workload["source"]: raise BudgetConfigurationError(f"{wid}: positive version and source required")
        for profile in ("development", "minimum_target"):
            metrics = workload.get("budgets", {}).get(profile, {})
            if not metrics: raise BudgetConfigurationError(f"{wid}: missing {profile} budgets")
            for key, rule in metrics.items():
                if profile == "development" and key in seen: raise BudgetConfigurationError(f"duplicate metric key: {key}")
                if not isinstance(key, str) or not key or set(rule) != {"unit", "limit", "class"} or rule["class"] not in CLASSES: raise BudgetConfigurationError(f"{wid}.{key}: invalid rule")
                if rule["unit"] not in UNITS_BY_CLASS[rule["class"]] or isinstance(rule["limit"], bool) or not isinstance(rule["limit"], (int,float)) or rule["limit"] <= 0 or not math.isfinite(rule["limit"]): raise BudgetConfigurationError(f"{wid}.{key}: invalid unit or limit")
                if profile == "development": seen.add(key)
        dev = workload["budgets"]["development"]; target = workload["budgets"]["minimum_target"]
        if set(dev) != set(target): raise BudgetConfigurationError(f"{wid}: profiles must contain identical keys")
        for key in dev:
            if dev[key]["unit"] != target[key]["unit"] or dev[key]["class"] != target[key]["class"] or dev[key]["limit"] > target[key]["limit"]: raise BudgetConfigurationError(f"{wid}.{key}: invalid threshold relationship")
            if dev[key]["class"] == "deterministic_size" and dev[key]["limit"] != target[key]["limit"]: raise BudgetConfigurationError(f"{wid}.{key}: deterministic limits cannot have platform allowances")
    records = data.get("calibrationRecords", [])
    if not records: raise BudgetConfigurationError("calibration records are required")
    referenced = set(); record_ids = set()
    for record in records:
        workload_id = record.get("workload")
        if workload_id not in workloads or record.get("workloadVersion") != workloads[workload_id].get("version"): raise BudgetConfigurationError("calibration record has stale workload reference")
        if not record.get("id") or record["id"] in record_ids: raise BudgetConfigurationError("calibration record ids must be present and unique")
        if workload_id in referenced: raise BudgetConfigurationError(f"{workload_id}: multiple calibration records are ambiguous")
        if not record.get("environment") or not record.get("aggregation") or not record.get("rationale") or not record.get("samples"): raise BudgetConfigurationError("calibration record lacks environment, aggregation, rationale, or samples")
        expected = set(workloads[workload_id]["budgets"]["development"])
        if set(record["samples"]) != expected: raise BudgetConfigurationError(f"{workload_id}: calibration samples must match budget keys")
        for key, value in record["samples"].items():
            if isinstance(value, bool) or not isinstance(value, (int,float)) or value < 0 or not math.isfinite(value): raise BudgetConfigurationError(f"invalid calibration sample {key}")
            if value > workloads[workload_id]["budgets"]["development"][key]["limit"]: raise BudgetConfigurationError(f"{workload_id}.{key}: calibration exceeds development budget")
        record_ids.add(record["id"]); referenced.add(workload_id)
    if referenced != set(workloads): raise BudgetConfigurationError("every workload requires a calibration record")
    policy = data.get("policy", {})
    if policy.get("aggregation") != "nearest_rank_p95" or policy.get("boundary") != "inclusive" or not policy.get("varianceAction") or not 0 <= policy.get("maximumTimingCoefficientOfVariation", -1) <= 1: raise BudgetConfigurationError("invalid aggregation, boundary, or variance policy")
    allowance = policy.get("platformAllowances", {}).get("minimum_target", {})
    if set(allowance) != {"timingMultiplier", "classes"} or allowance["classes"] != ["timing"] or not isinstance(allowance["timingMultiplier"], (int, float)) or allowance["timingMultiplier"] < 1: raise BudgetConfigurationError("invalid minimum-target platform allowance")
    for wid, workload in workloads.items():
        for key, rule in workload["budgets"]["development"].items():
            target = workload["budgets"]["minimum_target"][key]
            if rule["class"] == "timing" and target["limit"] > rule["limit"] * allowance["timingMultiplier"]: raise BudgetConfigurationError(f"{wid}.{key}: minimum-target timing allowance exceeded")
    return data

def compare(config, profile, reports):
    if profile not in {"development", "minimum_target"}: raise BudgetConfigurationError("unknown profile")
    failures=[]; measurements={}
    for workload_id, workload in sorted(config["workloads"].items()):
        report=reports.get(workload_id)
        if not report:
            failures.append({"kind":"correctness","workload":workload_id,"subsystem":"report","message":"required report is missing"}); continue
        if report.get("workloadVersion") != workload["version"]:
            failures.append({"kind":"correctness","workload":workload_id,"subsystem":"report","message":"workload version mismatch"}); continue
        for error in report.get("correctnessFailures", []):
            failures.append({"kind":"correctness","workload":workload_id,"subsystem":error.get("subsystem","unknown"),"map":error.get("map"),"message":error.get("message","correctness failure")})
        values=report.get("measurements", {}); cv=report.get("timingCoefficientOfVariation", {})
        expected=set(workload["budgets"][profile])
        if not isinstance(values, dict) or set(values) != expected:
            failures.append({"kind":"correctness","workload":workload_id,"subsystem":report.get("subsystem",workload_id),"map":report.get("map"),"message":"measurement keys do not match the versioned workload"})
            values = values if isinstance(values, dict) else {}
        for key, rule in sorted(workload["budgets"][profile].items()):
            observed=values.get(key); measurements[key]=observed
            context={"workload":workload_id,"subsystem":report.get("subsystem",workload_id),"map":report.get("map")}
            if not isinstance(observed,(int,float)) or isinstance(observed,bool) or not math.isfinite(observed): failures.append({"kind":"correctness","metric":key,**context,"message":f"{key}: measurement missing or invalid"}); continue
            if rule["class"] == "timing":
                variation = cv.get(key)
                if isinstance(variation, bool) or not isinstance(variation, (int, float)) or not math.isfinite(variation) or variation < 0:
                    failures.append({"kind":"correctness","metric":key,**context,"message":f"{key}: timing coefficient of variation missing or invalid"})
                elif variation > config["policy"]["maximumTimingCoefficientOfVariation"]:
                    failures.append({"kind":"variance","metric":key,"observed":variation,"limit":config["policy"]["maximumTimingCoefficientOfVariation"],**context,"message":f"{key}: timing variance exceeds policy; rerun on an idle permitted environment"})
            if observed > rule["limit"]:
                kind="timing_regression" if rule["class"] == "timing" else "deterministic_size_limit"
                failures.append({"kind":kind,"metric":key,"observed":observed,"limit":rule["limit"],"unit":rule["unit"],**context,"message":f"{key}: {observed:g} {rule['unit']} exceeds {profile} limit {rule['limit']:g}"})
    return {"format":REPORT_FORMAT,"budgetVersion":config["budgetVersion"],"profile":profile,"status":"pass" if not failures else "failure","passed":not failures,"measurements":measurements,"failures":failures}
