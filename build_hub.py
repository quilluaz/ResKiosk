"""Build the ResKiosk Hub executable using PyInstaller."""
import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
spec = os.path.join("packaging", "reskiosk-hub.spec")
result = subprocess.run(
    [sys.executable, "-m", "PyInstaller", spec, "--noconfirm"],
    cwd=os.path.dirname(os.path.abspath(__file__)),
)
sys.exit(result.returncode)
