# аналог black $ARGUMENTS

import json
import os
import subprocess
import sys

data = json.load(sys.stdin)
path = data.get("tool_input", {}).get("file_path", "")

if path and path.endswith(".py") and os.path.exists(path):
    subprocess.run(["black", path], check=False)
