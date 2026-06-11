import json
import sys

DANGEROUS_PATTERNS = ["rm -rf"]

input_data = sys.stdin.read()
tool_args: dict = json.loads(input_data)
tool_input = tool_args.get("tool_input", {})

command = tool_input.get("command", "").lower()

if any(pattern in command for pattern in DANGEROUS_PATTERNS):
    print(f"Blocked dangerous command: {command}", file=sys.stderr)
    sys.exit(2)

sys.exit(0)
