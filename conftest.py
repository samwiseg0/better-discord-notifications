import logging
import sys
import os

# Pre-configure the root logger so the module-level logging.basicConfig calls
# in radarr_notify / sonarr_notify are no-ops (basicConfig skips when handlers exist).
# This prevents log files being created in unexpected locations during tests.
logging.root.addHandler(logging.NullHandler())

sys.path.insert(0, os.path.dirname(__file__))
