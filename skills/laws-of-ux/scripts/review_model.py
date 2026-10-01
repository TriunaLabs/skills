"""Validation shared by the Laws of UX command-line helpers."""
from __future__ import annotations

PRINCIPLES = {"Hick's Law", "Miller's Law", "Fitts's Law", "Jakob's Law", "Postel's Law", "Tesler's Law", "Parkinson's Law", "Doherty Threshold", "Peak-End Rule", "Zeigarnik Effect", "Zeigarnik", "Goal-Gradient Effect", "Goal-Gradient", "Von Restorff Effect", "Von Restorff", "Serial Position Effect", "Serial position", "Pareto Principle", "Occam's Razor", "Proximity", "Similarity", "Pragnanz", "Prägnanz", "Uniform Connectedness", "Common Region"}
SEVERITIES = {"critical", "high", "medium", "low"}
SOURCE_TYPES = {"url", "screenshot", "html", "description", "trace"}

def validate_review(data: object, poster: bool = False) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict): return ["root must be an object"]
    if data.get("schema_version") != "2.0": errors.append("schema_version must be '2.0'")
    source = data.get("source")
    if not isinstance(source, dict) or source.get("type") not in SOURCE_TYPES or not source.get("ref"): errors.append("source requires a supported type and non-empty ref")
    findings = data.get("findings")
    if not isinstance(findings, list) or not findings: return errors + ["findings must be a non-empty array"]
    if poster and len(findings) > 14: errors.append("poster supports at most 14 findings")
    ids, evidence_pairs = set(), set()
    for index, finding in enumerate(findings, 1):
        label = f"finding {index}"
        if not isinstance(finding, dict): errors.append(f"{label} must be an object"); continue
        finding_id = finding.get("id")
        if not isinstance(finding_id, str) or not finding_id.strip(): errors.append(f"{label} requires id")
        elif finding_id in ids: errors.append(f"duplicate finding id: {finding_id}")
        else: ids.add(finding_id)
        if finding.get("n") != index: errors.append(f"{label} n must be {index}")
        if finding.get("side") not in {None, "left", "right"}: errors.append(f"{label} side must be left or right")
        for field in ("surface", "region", "observation", "evidence_ref", "mechanism", "recommendation"):
            if not isinstance(finding.get(field), str) or not finding[field].strip(): errors.append(f"{label} requires {field}")
        if finding.get("principle") not in PRINCIPLES: errors.append(f"{label} has unsupported principle: {finding.get('principle')!r}")
        if finding.get("severity") not in SEVERITIES: errors.append(f"{label} severity must be critical, high, medium, or low")
        confidence = finding.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1: errors.append(f"{label} confidence must be a number from 0 to 1")
        verification = finding.get("verification")
        if not isinstance(verification, list) or not verification or not all(isinstance(v, str) and v.strip() for v in verification): errors.append(f"{label} verification must contain at least one non-empty step")
        anchor = finding.get("anchor")
        if not isinstance(anchor, dict) or any(not isinstance(anchor.get(k), (int, float)) or isinstance(anchor.get(k), bool) or not 0 <= anchor[k] <= 1 for k in ("x", "y")): errors.append(f"{label} anchor x and y must be numbers from 0 to 1")
        pair = (str(finding.get("region", "")).strip().lower(), str(finding.get("observation", "")).strip().lower())
        if all(pair):
            if pair in evidence_pairs: errors.append(f"{label} duplicates an existing region and observation")
            evidence_pairs.add(pair)
    return errors
