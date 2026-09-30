"""Compatibility entrypoint for the richer CSV analyzer."""
from analyze_csv import main, profile

if __name__ == "__main__":
    main(default_format="json")
