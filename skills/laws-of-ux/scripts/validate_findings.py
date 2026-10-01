#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from review_model import validate_review

def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a Laws of UX review")
    parser.add_argument("findings"); parser.add_argument("--poster", action="store_true")
    args = parser.parse_args(); data = json.loads(Path(args.findings).read_text(encoding="utf-8"))
    errors = validate_review(data, poster=args.poster)
    if errors: raise SystemExit("Invalid review:\n- " + "\n- ".join(errors))
    print(f"valid: {args.findings} ({len(data['findings'])} findings)")
if __name__ == "__main__": main()
