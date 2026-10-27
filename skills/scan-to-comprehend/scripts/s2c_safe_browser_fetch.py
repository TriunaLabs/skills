#!/usr/bin/env python3
"""Fetch one browser resource through the public-IP-pinned S2C transport."""

from __future__ import annotations

import argparse
import base64
import json
import sys

from s2c_site_basics import get_public


MAX_RESOURCE_BYTES = 2_000_000


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    args = parser.parse_args()
    try:
        status, headers, body = get_public(args.url, MAX_RESOURCE_BYTES, timeout=8)
    except (OSError, ValueError) as error:
        print(json.dumps({"error": type(error).__name__}), flush=True)
        return 2
    selected = {key: value for key, value in headers.items()
                if key in {"content-type", "location", "cache-control"}}
    print(json.dumps({"status": status, "headers": selected,
                      "body_base64": base64.b64encode(body).decode("ascii")}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
