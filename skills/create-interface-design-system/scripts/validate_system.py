#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from design_model import validate_system

def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a generated interface design system")
    parser.add_argument("system")
    args = parser.parse_args(); data = json.loads(Path(args.system).read_text(encoding="utf-8"))
    errors = validate_system(data)
    if errors: raise SystemExit("Invalid design system:\n- " + "\n- ".join(errors))
    print(f"valid: {args.system}")
if __name__ == "__main__": main()
