# аналог jq . > input-log.json

import json
import os
import sys

data = json.load(sys.stdin)
log_path = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."), "input-log.json")

with open(log_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
