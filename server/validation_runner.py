"""
Run clinical validation benchmark.

Usage: python validation_runner.py [--verbose]
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.validation import ValidationRunner

if __name__ == "__main__":
    verbose = "--verbose" in sys.argv
    runner = ValidationRunner()
    results = runner.run_benchmark()
    ValidationRunner.print_report(results)
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    if passed < total:
        sys.exit(1)