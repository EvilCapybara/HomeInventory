import json
import sys
from pathlib import Path


input_data = sys.stdin.read()

tool_args: dict = json.loads(input_data)

tool_input = tool_args.get("tool_input", {})

path = Path(tool_input.get("file_path") or tool_input.get("path") or "")

if ".." in path.parts:
    print("Path traversal detected")
    sys.exit(2)

blocked = [".env", ".gitignore"]

if any(item in path for item in blocked):  
    print("Access denied", file=sys.stderr)
    sys.exit(2)

sys.exit(0)