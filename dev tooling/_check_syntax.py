import py_compile
import sys

files = [
    "hub/db/schema.py",
    "hub/db/init_db.py",
    "hub/db/migrate_schema.py",
    "hub/models/api_models.py",
    "hub/api/routes_admin.py",
    "hub/api/routes_query.py",
    "hub/bulk_kb_import.py",
    "hub/direct_check.py",
    "hub/retrieval/formatter.py",
    "hub/db/seed.py",
    "hub/db/evac_sync.py",
    "hub/retrieval/search.py",
    "hub/api/routes_kb.py",
    "hub/main.py",
]

errors = 0
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  OK: {f}")
    except py_compile.PyCompileError as e:
        print(f"  FAIL: {f}: {e}")
        errors += 1

if errors:
    print(f"\n{errors} file(s) have syntax errors!")
    sys.exit(1)
else:
    print(f"\nAll {len(files)} files compile OK")
