#!/usr/bin/env python3
"""Deterministic crawler, passage retrieval, and attention-gap projections."""

from __future__ import annotations

from collections import Counter
import math
import re

import s2c_scoring_profile


BOILERPLATE = {"header", "banner", "nav", "navigation", "footer", "contentinfo", "aside", "complementary"}
GENERIC_LINKS = {"click here", "read more", "learn more", "more", "here", "→"}
STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "do", "for", "from", "how", "i", "in", "is", "it", "of", "on", "or", "the", "this", "to", "what", "where", "with"}
TOKEN = re.compile(r"[\w]+", re.UNICODE)


def words(value: object) -> list[str]:
    return [word for word in TOKEN.findall(str(value or "").lower()) if word not in STOP]


def visible(node: dict) -> bool:
    return bool(node.get("visible")) and not node.get("aria_hidden")


def crawler(frame: dict, weights: dict | None = None) -> dict:
    weights = weights or s2c_scoring_profile.default_profile()["crawler_weights"]
    head = frame.get("head") or {}
    nodes = frame["nodes"]
    headings = [n for n in nodes if n.get("tag") in {"h1", "h2", "h3", "h4", "h5", "h6"} and visible(n)]
    first_h1 = next((n["id"] for n in headings if n["tag"] == "h1"), None)
    first_para = next((n["id"] for n in nodes if n.get("tag") == "p" and visible(n) and n.get("landmark") not in BOILERPLATE), None)
    meta = str(head.get("meta_description") or "")
    rows = []
    for node in nodes:
        tag, name = node.get("tag"), str(node.get("name") or node.get("text") or "").strip()
        weight, rule, flag = 0.0, "not weighted", None
        if not visible(node):
            rule = "hidden from this projection"
        elif tag == "h1":
            weight, rule = (weights["first_h1"], "first H1") if node["id"] == first_h1 else (weights["additional_h1"], "additional H1")
        elif tag == "h2":
            weight, rule = weights["h2"], "H2"
        elif tag in {"h3", "h4", "h5", "h6"}:
            weight, rule = weights["h3_h6"], "H3–H6"
        elif tag == "a":
            if not name:
                flag, rule = "empty_link_name", "link without captured name"
            elif name.lower() in GENERIC_LINKS or len(words(name)) < 2:
                weight, rule = weights["weak_link"], "weak link label"
            else:
                weight, rule = weights["descriptive_link"], "descriptive link label"
        elif tag == "img":
            alt = node.get("alt")
            if alt is None:
                flag, rule = "missing_alt", "image without alt attribute"
            elif not str(alt).strip():
                rule = "empty alt; inspect whether decorative"
            elif len(str(alt).strip()) < 4 or re.search(r"\.(png|jpe?g|webp|svg)$", str(alt), re.I):
                weight, rule = weights["weak_alt"], "weak image alt"
            else:
                weight, rule = weights["descriptive_alt"], "descriptive image alt"
        elif tag == "p" and node.get("landmark") not in BOILERPLATE:
            weight, rule = weights["paragraph"] * min(1, len(words(node.get("text"))) / 40), "body paragraph length"
        if node.get("landmark") in BOILERPLATE and weight:
            weight *= weights["boilerplate_multiplier"]
            rule += "; boilerplate damped"
        if node["id"] == first_h1 and head.get("title"):
            weight += weights["title_proxy"]
            rule += "; document title proxy"
        if node["id"] == first_para and meta:
            weight += weights["meta_in_range"] if 50 <= len(meta) <= 160 else weights["meta_out_of_range"]
            rule += "; meta description proxy"
        rows.append({"id": node["id"], "label": name[:100] or tag or "element", "weight": round(weight, 4),
                     "rule": rule, "flag": flag, "box": node.get("box"), "in_viewport": node.get("in_viewport", False)})
    levels = [int(n["tag"][1]) for n in headings]
    checks = [
        {"label": "Document title", "status": "present" if head.get("title") else "warning", "detail": f"{len(str(head.get('title') or ''))} characters"},
        {"label": "Meta description", "status": "present" if meta else "warning", "detail": f"{len(meta)} characters"},
        {"label": "H1 count", "status": "present" if levels.count(1) == 1 else "warning", "detail": str(levels.count(1))},
        {"label": "Heading level jumps", "status": "warning" if any(b > a + 1 for a, b in zip(levels, levels[1:])) else "present", "detail": "Review reading structure" if levels else "No headings captured"},
        {"label": "Canonical", "status": "present" if head.get("canonical") else "warning", "detail": "Captured head only"},
        {"label": "Page language", "status": "present" if head.get("lang") else "warning", "detail": str(head.get("lang") or "missing")},
        {"label": "Robots meta", "status": "present" if head.get("robots_meta") else "not checked", "detail": str(head.get("robots_meta") or "No directive captured")},
        {"label": "robots.txt, sitemap, JSON-LD", "status": "not checked", "detail": "Outside this capture"},
    ]
    return {"version": "s2c-crawler-v1", "nodes": rows, "checks": checks}


def chunks_for(frame: dict, max_words: int = 250) -> tuple[list[dict], list[dict]]:
    retained, removed = [], []
    for node in sorted(frame["nodes"], key=lambda n: (n.get("a11y_index") is None, n.get("a11y_index") or n.get("dom_index") or 0)):
        if not visible(node):
            continue
        if node.get("landmark") in BOILERPLATE:
            if node.get("in_viewport"):
                removed.append({"id": node["id"], "box": node.get("box"), "reason": "boilerplate landmark"})
            continue
        if node.get("tag") in {"h1", "h2", "h3", "p"} and str(node.get("text") or "").strip():
            retained.append(node)
    chunks, current, heading = [], [], ""
    def flush() -> None:
        if current:
            text = " ".join(str(n["text"]).strip() for n in current)
            chunks.append({"index": len(chunks) + 1, "heading": heading, "text": text,
                           "word_count": len(TOKEN.findall(text)), "node_ids": [n["id"] for n in current],
                           "boxes": [{"id": n["id"], "box": n.get("box"), "in_viewport": n.get("in_viewport", False)} for n in current]})
    for node in retained:
        tag = node["tag"]
        if tag in {"h1", "h2", "h3"}:
            flush()
            current = [node]
            heading = str(node["text"]).strip()[:120]
        else:
            if current and sum(len(TOKEN.findall(str(n.get("text") or ""))) for n in current) + len(TOKEN.findall(node["text"])) > max_words:
                flush()
                current = []
            current.append(node)
    flush()
    return chunks, removed


def retrieval(frame: dict, question: str = "", controls: dict | None = None) -> dict:
    controls = controls or s2c_scoring_profile.default_profile()["retrieval"]
    chunks, removed = chunks_for(frame, controls["max_words"])
    query = words(question)
    if query and chunks:
        counts = [Counter(words(chunk["text"])) for chunk in chunks]
        average = sum(sum(count.values()) for count in counts) / len(counts) or 1
        for chunk, count in zip(chunks, counts):
            length = sum(count.values())
            score = 0.0
            matched = []
            for term in sorted(set(query)):
                df = sum(term in row for row in counts)
                if not df or not count[term]:
                    continue
                matched.append(term)
                idf = math.log(1 + (len(chunks) - df + 0.5) / (df + 0.5))
                k1, b = controls["k1"], controls["b"]
                score += idf * count[term] * (k1 + 1) / (count[term] + k1 * (1 - b + b * length / average))
            chunk["score"] = round(score, 5)
            chunk["matched_terms"] = matched
    else:
        priors = controls["position_priors"]
        for index, chunk in enumerate(chunks):
            chunk["score"] = round(priors[min(index, 3)] * min(1, chunk["word_count"] / controls["length_target"]), 5)
            chunk["matched_terms"] = []
    maximum = max((chunk["score"] for chunk in chunks), default=0)
    for chunk in chunks:
        chunk["relative_score"] = round(chunk["score"] / maximum, 4) if maximum else 0
    return {"version": "s2c-retrieval-v1", "question": question, "mode": "bm25" if query else "position-length prior",
            "parameters": controls,
            "chunks": chunks, "removed": removed, "main_word_count": sum(c["word_count"] for c in chunks),
            "checks": [{"label": "Retained text", "status": "present" if chunks else "warning", "detail": f"{sum(c['word_count'] for c in chunks)} words in {len(chunks)} chunks"},
                       {"label": "robots.txt and llms.txt", "status": "not checked", "detail": "Outside this capture"}]}


def percentile_map(values: dict[str, float], ids: list[str]) -> dict[str, float]:
    ordered = sorted(ids, key=lambda key: (-values.get(key, 0), key))
    ranks = {}
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values.get(ordered[end], 0) == values.get(ordered[start], 0):
            end += 1
        percentile = 1 - ((start + end - 1) / 2) / max(1, len(ordered) - 1)
        for key in ordered[start:end]:
            ranks[key] = percentile
        start = end
    return ranks


def gaps(frame: dict, crawler_view: dict, retrieval_view: dict, assistive_frame: dict | None, attention_frame: dict | None,
         threshold: float = 0.4) -> dict:
    if not attention_frame:
        return {"version": "s2c-gap-v1", "available": False, "reason": "Attention projection was skipped."}
    nodes = {n["id"]: n for n in frame["nodes"] if n.get("in_viewport") and visible(n)}
    attention = {cue["id"]: float(cue.get("weight") or 0) for cue in attention_frame.get("cues", []) if cue.get("id") in nodes}
    crawler_weights = {row["id"]: row["weight"] for row in crawler_view["nodes"]}
    retrieval_weights = {key: chunk["relative_score"] for chunk in retrieval_view["chunks"] for key in chunk["node_ids"]}
    reading = {step.get("id"): 1 / step["index"] for step in (assistive_frame or {}).get("reading_path", [])[:10] if step.get("id")}
    # Compare only nodes represented by the experimental attention estimate.
    ids = sorted(set(nodes) & set(attention))
    human_rank = percentile_map(attention, ids)
    comparisons = []
    for label, weights in (("crawler", crawler_weights), ("retrieval", retrieval_weights), ("assistive", reading)):
        other_rank = percentile_map(weights, ids)
        for key in ids:
            delta = round(human_rank[key] - other_rank[key], 3)
            if abs(delta) < threshold:
                continue
            node = nodes[key]
            comparisons.append({"reader": label, "id": key, "label": str(node.get("name") or node.get("text") or node.get("alt") or node.get("tag"))[:100],
                                "box": node.get("box"), "difference": delta,
                                "direction": "attention higher" if delta > 0 else f"{label} higher",
                                "reason": next((row["rule"] for row in crawler_view["nodes"] if row["id"] == key), "captured order or chunk rule") if label == "crawler" else ("retained passage text" if label == "retrieval" else "first ten AX reading steps")})
    comparisons.sort(key=lambda row: -abs(row["difference"]))
    return {"version": "s2c-gap-v1", "available": True, "method": "node-rank percentile difference",
            "rank_threshold": threshold,
            "comparisons": comparisons[:20], "compared_nodes": len(ids)}


def project(snapshot: dict, assistive: dict, attention: dict | None = None, question: str = "",
            profile: dict | None = None) -> dict:
    if snapshot.get("schema") != "s2c-browser-capture/v1" or assistive.get("schema") != "s2c-assistive-v1":
        raise ValueError("Expected S2C browser and assistive v1 results")
    if not isinstance(question, str) or len(question) > 200:
        raise ValueError("Retrieval question must be at most 200 characters")
    profile = s2c_scoring_profile.validate(profile or s2c_scoring_profile.default_profile())
    assistive_frames = {f["id"]: f for f in assistive["frames"]}
    attention_frames = {f["id"]: f for f in (attention or {}).get("frames", [])}
    frames = []
    for frame in snapshot["frames"]:
        crawler_view = crawler(frame, profile["crawler_weights"])
        retrieval_view = retrieval(frame, question.strip(), profile["retrieval"])
        frames.append({"id": frame["id"], "image": frame["image"], "viewport": frame["viewport"],
                       "captured_at": frame["captured_at"], "crawler": crawler_view, "retrieval": retrieval_view,
                       "gap": gaps(frame, crawler_view, retrieval_view, assistive_frames.get(frame["id"]),
                                   attention_frames.get(frame["id"]), profile["gap"]["rank_threshold"])})
    return {"schema": "s2c-reader-views/v1", "url": snapshot["url"], "audited_on": snapshot["audited_on"],
            "question": question.strip(), "profile": profile, "frames": frames}
