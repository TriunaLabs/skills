#!/usr/bin/env python3
"""Project a Chromium S2C capture into an assistive reading review."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path


def project(snapshot: dict) -> dict:
    if snapshot.get("schema") != "s2c-browser-capture/v1":
        raise ValueError("Expected s2c-browser-capture/v1")
    frames = []
    for frame in snapshot["frames"]:
        nodes = {node["id"]: node for node in frame["nodes"]}
        reading = []
        for step in frame["ax_path"]:
            if step["role"] == "RootWebArea" or not step["name"].strip():
                continue
            if step["role"] == "StaticText" and reading and reading[-1]["name"].strip() == step["name"].strip():
                continue
            node = nodes.get(step.get("id"))
            reading.append({"index": len(reading) + 1, "ax_index": step["index"],
                            "id": step.get("id"), "role": step["role"], "name": step["name"],
                            "box": node["box"] if node else None,
                            "in_viewport": bool(node and node["in_viewport"])})
        focus = []
        findings = []
        for step in frame["focus_path"]:
            node = nodes.get(step.get("id"))
            box = node["box"] if node else step["box"]
            name = (node.get("name") if node else None) or step["label"]
            focus.append({**step, "label": name, "box": box,
                          "in_viewport": bool(node and node["in_viewport"])})
            if not name.strip():
                findings.append({"kind": "name_review", "id": step.get("id"),
                                 "message": f"Keyboard step {step['index']} has no captured accessible name; inspect the control."})
            if (box["width"] < 24 or box["height"] < 24) and (step["tag"] != "a" or (box["width"] < 24 and box["height"] < 24)):
                findings.append({"kind": "target_review", "id": step.get("id"),
                                 "message": f"Keyboard step {step['index']} measures {box['width']:.0f} × {box['height']:.0f} CSS px. Check WCAG 2.5.8 spacing and exceptions."})
        for node in frame["nodes"]:
            if node["tag"] == "img" and node["visible"] and node["alt"] is None:
                findings.append({"kind": "alt_review", "id": node["id"],
                                 "message": "Visible image has no alt attribute; inspect whether it carries content or is decorative."})
            if node.get("clipped_text"):
                findings.append({"kind": "clip_review", "id": node["id"],
                                 "message": f"Text in {node['tag']} may be horizontally clipped; inspect at {frame['viewport']['width']} px."})
        if frame["document_width"] > frame["client_width"] + 1:
            findings.insert(0, {"kind": "reflow_review", "id": None,
                                "message": f"Document is {frame['document_width']} CSS px wide in a {frame['client_width']} px viewport; inspect horizontal scrolling."})
        first_heading = next((step for step in reading if step["role"] == "heading"), None)
        action_words = ("waitlist", "join", "early access", "sign up", "request", "book", "start")
        first_action = next((step for step in reading if step["role"] in ("button", "link")
                             and any(word in step["name"].lower() for word in action_words)), None)
        frames.append({"id": frame["id"], "image": frame["image"], "url": frame["url"],
                       "captured_at": frame["captured_at"], "viewport": frame["viewport"],
                       "reading_path": reading, "focus_path": focus, "findings": findings,
                       "first_heading_step": first_heading["index"] if first_heading else None,
                       "first_action_step": first_action["index"] if first_action else None,
                       "focus_stop": frame["focus_stop"],
                       "document_width": frame["document_width"], "client_width": frame["client_width"]})
    audited_on = snapshot["audited_on"]
    date.fromisoformat(audited_on)
    return {"schema": "s2c-assistive-v1", "audited_on": audited_on,
            "url": snapshot["url"], "frames": frames,
            "basis": "Chromium accessibility tree and observed browser Tab traversal",
            "limit": "This is a browser projection, not a screen reader speech trace or WCAG conformance audit. Target-size, names, alternatives, and clipping are review candidates."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = project(json.loads(args.snapshot.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
