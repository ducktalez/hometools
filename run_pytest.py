#!/usr/bin/env python
"""Run pytest tests directly."""
import pytest
import sys

# Run specific tests
exit_code = pytest.main([
    "tests/test_offline_downloads.py",
    "tests/test_feature_parity.py",
    "-v",
    "--tb=short"
])

print(f"\n\nTest exit code: {exit_code}")
sys.exit(exit_code)

