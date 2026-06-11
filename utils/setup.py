from pathlib import Path

project_dir = Path.cwd().resolve()

with open("settings.example.json", "r", encoding="utf-8") as f:
    config = f.read()

config = config.replace("$PWD", str(project_dir))

with open("settings.local.json", "w", encoding="utf-8") as f:
    f.write(config)

print("settings.local.json generated")