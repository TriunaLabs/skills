#!/usr/bin/env python3
"""Score explicit browser checks, with editable editorial weights and coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "references/browser-rubric.json"
RULES = {
    "nav_shared_fragment": "Distinct navigation labels use distinct in-page destinations",
    "one_page_h1": "One visible page-level heading in the captured DOM",
    "h1_in_first_view": "Page-level heading appears in each first viewport",
    "narrow_reflow": "No document-level overflow at 320 CSS px",
    "named_focus_controls": "Captured focus controls have names",
    "image_alt_attribute": "Visible images have alt attributes",
    "solid_text_contrast": "Supplied solid-color text clears reference contrast thresholds",
}


def weights_from(config: dict) -> dict[str, int]:
    if config.get("schema") != "s2c-browser-rubric-config/v1":
        raise ValueError("Expected s2c-browser-rubric-config/v1")
    weights = config.get("weights")
    if not isinstance(weights, dict) or set(weights) != set(RULES):
        raise ValueError("Rubric weights must name each supported rule exactly once")
    if any(type(value) is not int or value < 0 or value > 100 for value in weights.values()):
        raise ValueError("Rubric weights must be integer points from 0 to 100")
    if sum(weights.values()) != 100:
        raise ValueError("Rubric weights must sum to 100")
    return weights


def evaluate(snapshot: dict, assistive: dict | None = None, attention: dict | None = None,
             config: dict | None = None) -> dict:
    if snapshot.get("schema") != "s2c-browser-capture/v1":
        raise ValueError("Expected s2c-browser-capture/v1")
    if assistive is not None and (assistive.get("schema") != "s2c-assistive-v1"
                                  or assistive.get("audited_on") != snapshot.get("audited_on")):
        raise ValueError("Assistive result must match the capture and audit date")
    if attention is not None and attention.get("schema") != "s2c-attention/v1":
        raise ValueError("Expected s2c-attention/v1")
    if config is None:
        config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    weights = weights_from(config)
    frames = snapshot.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("Browser capture needs frames")
    desktop = frames[0]
    results: dict[str, tuple[str, list[str], str]] = {}

    nav_links = [node for node in desktop["nodes"] if node.get("tag") == "a" and node.get("landmark") == "nav"
                 and isinstance(node.get("href"), str) and node["href"].startswith("#")]
    destinations: dict[str, set[str]] = {}
    for node in nav_links:
        label = (node.get("name") or node.get("text") or "").strip()
        if label:
            destinations.setdefault(node["href"], set()).add(label)
    duplicates = [(href, sorted(labels)) for href, labels in destinations.items() if len(labels) > 1]
    if not nav_links:
        results["nav_shared_fragment"] = ("not_checked", ["No named in-page navigation links captured."], "Inspect navigation manually.")
    elif duplicates:
        evidence = [f"{', '.join(labels)} all target {href}." for href, labels in duplicates]
        results["nav_shared_fragment"] = ("warning", evidence,
                                           "Give distinct navigation labels their intended section anchors; verify clicks from mid-page.")
    else:
        results["nav_shared_fragment"] = ("pass", [f"{len(nav_links)} named in-page navigation link(s) have no shared target across different labels."],
                                           "Preserve distinct destinations.")

    h1s = [node for node in desktop["nodes"] if node.get("heading_level") == 1 and node.get("visible")
           and not node.get("aria_hidden")]
    h1_count = len(h1s)
    results["one_page_h1"] = ("pass" if h1_count == 1 else "warning",
                               [f"Captured DOM contains {h1_count} visible H1 element(s)."],
                               "Keep one clear page title." if h1_count == 1 else
                               "Review page outline and use one clear page title unless the content structure justifies more.")
    missing_h1 = [str(frame.get("id")) for frame in frames if not any(
        node.get("heading_level") == 1 and node.get("in_viewport") and not node.get("aria_hidden")
        for node in frame["nodes"])]
    results["h1_in_first_view"] = ("warning" if missing_h1 else "pass",
                                    ["H1 absent from first viewport: " + ", ".join(missing_h1) + "." if missing_h1
                                     else f"A visible H1 appears in all {len(frames)} captured first viewports."],
                                    "Inspect the first-screen orientation at the affected width." if missing_h1
                                    else "Preserve first-screen heading clarity.")
    narrow = min(frames, key=lambda frame: frame["viewport"]["width"])
    if narrow["viewport"]["width"] > 320:
        results["narrow_reflow"] = ("not_checked", ["No viewport at or below 320 CSS px was captured."],
                                      "Capture a 320 CSS px viewport.")
    else:
        overflow = narrow["document_width"] - narrow["client_width"]
        results["narrow_reflow"] = ("warning" if overflow > 1 else "pass",
                                      [f"{narrow['id']}: document width {narrow['document_width']} px; client width {narrow['client_width']} px."],
                                      "Inspect the overflow source at 320 CSS px." if overflow > 1 else "Preserve the current narrow reflow.")

    if assistive is None:
        results["named_focus_controls"] = ("not_checked", ["No browser focus-path projection supplied."],
                                             "Run the assistive projection.")
        results["image_alt_attribute"] = ("not_checked", ["No browser assistive projection supplied."],
                                            "Run the assistive projection.")
    else:
        focus_frames = assistive["frames"]
        unnamed = [(frame["id"], finding["message"]) for frame in focus_frames for finding in frame.get("findings", [])
                   if finding.get("kind") == "name_review"]
        focus_total = sum(len(frame.get("focus_path", [])) for frame in focus_frames)
        results["named_focus_controls"] = (
            "warning" if unnamed else ("pass" if focus_total else "not_checked"),
            [f"{len(unnamed)} unnamed captured focus control(s) across {focus_total} Tab step(s)."]
            + [f"{frame}: {message}" for frame, message in unnamed[:5]],
            "Give each focusable control an accessible name; confirm in a screen reader." if unnamed else "Confirm names in a screen reader.")
        missing_alt = [(frame["id"], finding["message"]) for frame in focus_frames for finding in frame.get("findings", [])
                       if finding.get("kind") == "alt_review"]
        visible_images = sum(node.get("tag") == "img" and node.get("visible") for frame in frames for node in frame["nodes"])
        results["image_alt_attribute"] = (
            "review" if missing_alt else ("pass" if visible_images else "not_checked"),
            [f"{len(missing_alt)} visible image(s) lack alt attributes across {visible_images} captured image instances."],
            "Inspect each image's purpose; use meaningful alt text or an empty alt for decorative images." if missing_alt
            else "Review the quality and purpose of existing alt text.")

    if attention is None:
        results["solid_text_contrast"] = ("not_checked", ["No contrast screen supplied."], "Run the attention contrast projection.")
    else:
        checks = [check for frame in attention.get("frames", [])
                  for check in frame.get("text_contrast_spotcheck", {}).get("checks", [])]
        below = sum(check.get("status") == "below_threshold" for check in checks)
        unknown = sum(check.get("status") == "needs_review" for check in checks)
        known = sum(check.get("status") in {"below_threshold", "at_or_above_threshold"} for check in checks)
        status = "warning" if below else ("review" if unknown else ("pass" if known else "not_checked"))
        results["solid_text_contrast"] = (
            status, [f"{below} below reference threshold; {unknown} need review; {known} have supplied solid-color ratios."],
            "Verify actual painted backgrounds, font metrics and interaction states; fix confirmed low contrast." if below or unknown
            else "Preserve legible solid-color text and inspect other states.")

    rows = []
    for rule_id, title in RULES.items():
        status, evidence, suggestion = results[rule_id]
        weight = weights[rule_id]
        rows.append({"id": rule_id, "title": title, "status": status, "weight": weight,
                     "earned": weight if status == "pass" else 0, "evidence": evidence, "suggestion": suggestion})
    assessed = sum(row["weight"] for row in rows if row["status"] in {"pass", "warning"})
    earned = sum(row["earned"] for row in rows)
    return {"schema": "s2c-browser-rubric/v1", "audited_on": snapshot["audited_on"],
            "url": snapshot["url"], "rubric_version": str(config.get("version", "custom")),
            "score": {"earned": earned, "assessed": assessed, "possible": 100,
                      "percent_of_assessed": round(100 * earned / assessed) if assessed else None},
            "counts": {status: sum(row["status"] == status for row in rows)
                       for status in ("pass", "warning", "review", "not_checked")},
            "rules": rows,
            "limit": "Editorial checklist points for specific browser facts; review and not-checked rules are excluded from the assessed denominator. Not measured cognitive load, gaze, usability, or WCAG conformance."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--assistive", type=Path)
    parser.add_argument("--attention", type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    read = lambda path: json.loads(path.read_text(encoding="utf-8")) if path else None
    result = evaluate(read(args.snapshot), read(args.assistive), read(args.attention), read(args.config))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
