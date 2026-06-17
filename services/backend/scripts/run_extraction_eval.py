#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.modules.dialogue_agent.extraction_eval import run_extraction_eval  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ReiLink LLM-primary extraction eval scenarios.")
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=BACKEND_ROOT.parents[1] / "docs" / "qa" / "extraction_eval_scenarios.json",
        help="Path to extraction eval scenarios JSON.",
    )
    parser.add_argument(
        "--provider",
        choices=("mock", "live"),
        default="mock",
        help="Use deterministic mock payloads or the configured live provider.",
    )
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Exit 0 even if some scenarios fail.",
    )
    args = parser.parse_args()
    report = run_extraction_eval(scenarios_path=args.scenarios, provider_mode=args.provider)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    failed = int(report["metrics"]["failed"])
    return 0 if failed == 0 or args.allow_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
