import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())

try:
    from hub.main import app
    print("App imported successfully.")
    
    # Try to manually trigger startup logic
    from hub.db.init_db import init_db
    print("Running init_db()...")
    init_db()
    print("init_db() successful.")

    from hub.main import _start_federation
    print("Running _start_federation()...")
    _start_federation()
    print("_start_federation() successful.")

    print("All startup components tested successfully.")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
