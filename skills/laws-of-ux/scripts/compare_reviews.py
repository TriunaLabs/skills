#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from review_model import validate_review

def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two Laws of UX reviews")
    parser.add_argument("before"); parser.add_argument("after"); parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args(); before = json.loads(Path(args.before).read_text(encoding="utf-8")); after = json.loads(Path(args.after).read_text(encoding="utf-8"))
    errors = validate_review(before) + validate_review(after)
    if errors: raise SystemExit("Invalid review:\n- " + "\n- ".join(errors))
    left = {i["id"]: i for i in before["findings"]}; right = {i["id"]: i for i in after["findings"]}
    resolved = sorted(left.keys() - right.keys()); new = sorted(right.keys() - left.keys())
    def meaning(item): return {k: v for k, v in item.items() if k not in {"n", "side", "anchor", "evidence_ref"}}
    changed = sorted(k for k in left.keys() & right.keys() if meaning(left[k]) != meaning(right[k])); unchanged = sorted(k for k in left.keys() & right.keys() if meaning(left[k]) == meaning(right[k]))
    result = {"schema_version":"1.0","before":str(args.before),"after":str(args.after),"summary":{"resolved":len(resolved),"new":len(new),"changed":len(changed),"unchanged":len(unchanged)},"resolved":resolved,"new":new,"changed":changed,"unchanged":unchanged}
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8"); print(f"wrote {args.output}")
if __name__ == "__main__": main()
