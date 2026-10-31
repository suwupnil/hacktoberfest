#!/usr/bin/env python3
"""Root executable runner for Evidence-Based Issue Triage."""

import os
import sys

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from triage.cli import main

if __name__ == "__main__":
    main()
