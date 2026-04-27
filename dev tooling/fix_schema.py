"""
Quick fix: adds missing 'DateTime' and 'datetime' imports to hub/db/schema.py
Run with:  venv\Scripts\python.exe fix_schema.py
"""
import os

path = os.path.join(os.path.dirname(__file__), "hub", "db", "schema.py")
print(f"Target: {path}")

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Show current first line
first_line = content.split("\n")[0]
print(f"Current line 1: {first_line!r}")

if "from datetime import datetime" in content and "DateTime" in content.split("\n")[2]:
    print("File already patched!")
else:
    # Replace the import block
    old_import = "from sqlalchemy import (\n    Column, Integer, String, Text, Float, LargeBinary, ForeignKey, \n)"
    new_import = "from datetime import datetime\nfrom sqlalchemy import (\n    Column, Integer, String, Text, Float, LargeBinary, ForeignKey, DateTime\n)"

    if old_import in content:
        content = content.replace(old_import, new_import)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("PATCHED successfully!")
    else:
        print("Could not find expected import block. Current imports:")
        for i, line in enumerate(content.split("\n")[:5], 1):
            print(f"  {i}: {line!r}")

# Verify
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
print(f"\nVerification - first 5 lines:")
for i, line in enumerate(lines[:5], 1):
    print(f"  {i}: {line.rstrip()}")

# Clear pycache
import shutil
cache = os.path.join(os.path.dirname(path), "__pycache__")
if os.path.isdir(cache):
    shutil.rmtree(cache)
    print("\n__pycache__ cleared.")
