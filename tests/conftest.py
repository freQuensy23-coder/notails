"""Make scripts/detector.py importable as `detector` from the tests."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
