#!/usr/bin/env python3
"""Versioned, bounded editorial controls for reproducible S2C rescoring."""

from __future__ import annotations

import json
import hashlib
import math
from pathlib import Path

import s2c_browser_rubric


SCHEMA = "s2c-scoring-profile/v1"
CRAWLER_LABELS = {
    "first_h1": "First H1", "additional_h1": "Additional H1",
    "h2": "H2", "h3_h6": "H3–H6", "descriptive_link": "Descriptive link",
    "weak_link": "Weak link label", "descriptive_alt": "Descriptive image alt",
    "weak_alt": "Weak image alt", "paragraph": "Body paragraph maximum",
    "boilerplate_multiplier": "Header/nav/footer multiplier",
    "title_proxy": "Title proxy on H1", "meta_in_range": "Meta proxy, 50–160 chars",
    "meta_out_of_range": "Meta proxy, other length",
}


def default_profile() -> dict:
    browser = json.loads(s2c_browser_rubric.DEFAULT_CONFIG.read_text(encoding="utf-8"))
    return {"schema": SCHEMA, "version": "1.0.0",
            "browser_weights": browser["weights"],
            "crawler_weights": {
                "first_h1": 0.9, "additional_h1": 0.4, "h2": 0.55, "h3_h6": 0.35,
                "descriptive_link": 0.4, "weak_link": 0.1,
                "descriptive_alt": 0.35, "weak_alt": 0.1, "paragraph": 0.25,
                "boilerplate_multiplier": 0.5, "title_proxy": 1.0,
                "meta_in_range": 0.7, "meta_out_of_range": 0.35,
            },
            "retrieval": {"k1": 1.2, "b": 0.75, "max_words": 250,
                          "length_target": 80,
                          "position_priors": [1.0, 0.6, 0.4, 0.25]},
            "gap": {"rank_threshold": 0.4}}


def number(value: object, key: str, low: float, high: float, *, integer: bool = False) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{key} must be a finite number")
    if integer and type(value) is not int:
        raise ValueError(f"{key} must be an integer")
    if not low <= value <= high:
        raise ValueError(f"{key} must be between {low} and {high}")
    return value


def validate(profile: object) -> dict:
    if not isinstance(profile, dict) or set(profile) != {"schema", "version", "browser_weights", "crawler_weights", "retrieval", "gap"}:
        raise ValueError("Expected the complete S2C scoring profile")
    if profile["schema"] != SCHEMA or profile["version"] != "1.0.0":
        raise ValueError("Unsupported S2C scoring profile version")
    browser = profile["browser_weights"]
    s2c_browser_rubric.weights_from({"schema": "s2c-browser-rubric-config/v1", "weights": browser})
    crawler = profile["crawler_weights"]
    if not isinstance(crawler, dict) or set(crawler) != set(CRAWLER_LABELS):
        raise ValueError("Crawler weights must name each supported control exactly once")
    for key, value in crawler.items():
        number(value, f"crawler.{key}", 0, 1 if key == "boilerplate_multiplier" else 3)
    retrieval = profile["retrieval"]
    if not isinstance(retrieval, dict) or set(retrieval) != {"k1", "b", "max_words", "length_target", "position_priors"}:
        raise ValueError("Retrieval controls are incomplete")
    number(retrieval["k1"], "retrieval.k1", 0.1, 3)
    number(retrieval["b"], "retrieval.b", 0, 1)
    number(retrieval["max_words"], "retrieval.max_words", 50, 500, integer=True)
    number(retrieval["length_target"], "retrieval.length_target", 20, 250, integer=True)
    priors = retrieval["position_priors"]
    if not isinstance(priors, list) or len(priors) != 4:
        raise ValueError("Retrieval needs four position priors")
    for index, value in enumerate(priors):
        number(value, f"retrieval.position_priors[{index}]", 0, 1)
    gap = profile["gap"]
    if not isinstance(gap, dict) or set(gap) != {"rank_threshold"}:
        raise ValueError("Gap controls are incomplete")
    number(gap["rank_threshold"], "gap.rank_threshold", 0, 1)
    return json.loads(json.dumps(profile))


def read(path: Path | None) -> dict:
    return validate(json.loads(path.read_text(encoding="utf-8"))) if path else default_profile()


def fingerprint(profile: dict) -> str:
    canonical = json.dumps(validate(profile), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
