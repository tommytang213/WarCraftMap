#!/usr/bin/env python3
"""Execute a scenario's complete Wurst suite using the release assembly path."""
import argparse
from pathlib import Path

from package_wurst_map import PackagingError, load_config, run_execution_tests, validate_inputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--grill")
    parser.add_argument("--source-revision")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        run_execution_tests(config, validate_inputs(config, args.grill), args.source_revision)
    except (PackagingError, OSError) as error:
        parser.exit(1, f"Wurst execution failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
