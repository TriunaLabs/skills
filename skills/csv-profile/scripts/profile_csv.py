"""Read-only aggregate CSV profile; Python standard library only."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

def profile(path, delimiter=','):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream, delimiter=delimiter, strict=True)
        headers = next(reader, [])
        missing = [0] * len(headers)
        rows = mismatches = 0
        for row in reader:
            rows += 1
            if len(row) != len(headers):
                mismatches += 1
                continue
            for index, value in enumerate(row):
                missing[index] += not value.strip()
    return {'rows': rows, 'columns': len(headers),
            'duplicate_headers': [h for h, n in Counter(headers).items() if n > 1],
            'empty_headers': sum(not h.strip() for h in headers),
            'width_mismatches': mismatches,
            'missing_by_column_index': missing}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path')
    parser.add_argument('--delimiter', default=',')
    args = parser.parse_args()
    if len(args.delimiter) != 1:
        parser.error('--delimiter must be one character')
    try:
        print(json.dumps(profile(args.path, args.delimiter), indent=2))
    except (OSError, UnicodeError, csv.Error) as error:
        parser.exit(1, f'Unable to profile CSV: {error}\n')
