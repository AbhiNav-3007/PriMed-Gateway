"""
Pytest configuration file to automatically append current root directory to sys.path.
"""

import sys
from pathlib import Path

# Add project root directory to sys.path for test discovery
root_dir = Path(__file__).parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
