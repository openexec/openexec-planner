"""Configuration for pytest."""

import sys
from pathlib import Path

# Add src directory to path so imports work correctly
sys.path.insert(0, str(Path(__file__).parent))
