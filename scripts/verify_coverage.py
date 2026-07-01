"""
ELUSoC_2026 - Test Coverage Verification Script.
Ensures overall code coverage does not drop below required project thresholds.
"""

from __future__ import annotations

import json
import subprocess
import sys


def main() -> None:
    # Run coverage report in JSON format
    subprocess.run(["coverage", "json"], check=True)
    
    with open("coverage.json", "r") as f:
        data = json.load(f)
        
    percent = data["totals"]["percent_covered"]
    required_threshold = 70.0
    
    print(f"Current Code Coverage: {percent:.2f}%")
    print(f"Required Coverage Threshold: {required_threshold}%")
    
    if percent < required_threshold:
        print("Code coverage is below the required threshold! PR blocked.")
        sys.exit(1)
        
    print("Code coverage thresholds verified successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
