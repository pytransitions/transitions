import sys
import os.path

collect_ignore = []
current_dir = os.path.dirname(os.path.abspath(__file__))

if sys.version_info.major < 3:
    collect_ignore.append(os.path.join(current_dir, "test_async.py"))
