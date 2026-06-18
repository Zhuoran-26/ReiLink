#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.modules.dialogue_agent.persona_memory_eval import (  # noqa: E402
    assert_report_is_safe,
    run_persona_memory_eval,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ReiLink persona-memory regression eval scenarios.")
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=BACKEND_ROOT.parents[1] / "docs" / "qa" / "persona_memory_regression_scenarios.json",
        help="Path to persona-memory regression scenarios JSON.",
    )
    parser.add_argument(
        "--provider",
        choices=("mock", "live"),
        default="mock",
        help="Use deterministic mock replies or the configured live provider.",
    )
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Exit 0 even if some scenarios fail.",
    )
    args = parser.parse_args()
    report = run_persona_memory_eval(scenarios_path=args.scenarios, provider_mode=args.provider)
    assert_report_is_safe(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.provider == "live":
        failed = int(report["metrics"].get("hard_failed", report["metrics"]["failed"]))
    else:
        failed = int(report["metrics"]["failed"])
    return 0 if failed == 0 or args.allow_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
