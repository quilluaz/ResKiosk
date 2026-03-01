import os
import signal
import sys
import subprocess
import time
import webbrowser
import traceback
from pathlib import Path

# When frozen (PyInstaller), ensure bundle root is on path so "from hub import main" finds the hub package
if getattr(sys, "frozen", False):
    _bundle_root = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
    sys.path.insert(0, str(_bundle_root))

def get_base_path():
    """Get the base path for finding bundled data files."""
    if getattr(sys, 'frozen', False):
        # PyInstaller onedir: sys._MEIPASS = _internal dir
        if hasattr(sys, '_MEIPASS'):
            return Path(sys._MEIPASS)
        # Fallback: directory containing the exe
        return Path(sys.executable).parent
    # Dev mode: parent of hub/ directory
    return Path(__file__).parent.parent

def get_data_dir():
    """Get the persistent data directory for ResKiosk."""
    if os.name == 'nt':
        base = Path(os.environ.get('APPDATA', os.path.expanduser('~')))
        path = base / "ResKiosk"
    else:
        path = Path.home() / ".local" / "share" / "reskiosk"
    path.mkdir(parents=True, exist_ok=True)
    return path

def setup_env(base_path, data_path):
    """Configure environment variables."""
    is_dev = not getattr(sys, 'frozen', False)
    if is_dev:
        # Dev mode: models live under packaging/
        hub_models = base_path / "packaging" / "hub_models"
        ollama_models = base_path / "packaging" / "ollama_portable" / "models"
    else:
        hub_models = base_path / "hub_models"
        ollama_models = base_path / "ollama_portable" / "models"
    nllb_models = hub_models / "nllb"
    static_path = base_path / "console_static"

    os.environ["OLLAMA_MODELS"] = str(ollama_models)
    os.environ["RESKIOSK_DB_PATH"] = str(data_path / "reskiosk.db")
    os.environ["RESKIOSK_STATIC_PATH"] = str(static_path)
    os.environ["RESKIOSK_MODELS_PATH"] = str(hub_models)
    os.environ["RESKIOSK_NLLB_PATH"] = str(nllb_models)

    print(f"Environment configured:")
    print(f"  Base path: {base_path}")
    print(f"  Data path: {data_path}")
    print(f"  OLLAMA_MODELS: {os.environ['OLLAMA_MODELS']}")
    print(f"  RESKIOSK_NLLB_PATH: {os.environ['RESKIOSK_NLLB_PATH']}")
    print(f"  RESKIOSK_DB_PATH: {os.environ['RESKIOSK_DB_PATH']}")
    sys.stdout.flush()

def start_ollama(base_path):
    """Start bundled or system Ollama server. Returns process or None."""
    import shutil
    is_dev = not getattr(sys, 'frozen', False)

    # Check bundled locations
    candidates = [base_path / "ollama_portable" / "ollama.exe"]
    if is_dev:
        candidates.append(base_path / "packaging" / "ollama_portable" / "ollama.exe")

    ollama_exe = None
    for candidate in candidates:
        if candidate.exists():
            ollama_exe = candidate
            break

    # Fall back to system PATH (handles standard Ollama install)
    if ollama_exe is None:
        which = shutil.which("ollama")
        if which:
            ollama_exe = Path(which)
            print(f"Using system Ollama from PATH: {ollama_exe}")
        else:
            print("Warning: Ollama not found in bundle or system PATH.")
            print("Install Ollama from https://ollama.com to enable LLM formatting.")
            return None

    print(f"Starting bundled Ollama from {ollama_exe}...")
    sys.stdout.flush()
    
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        process = subprocess.Popen(
            [str(ollama_exe), "serve"],
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        # Write Ollama PID so dashboard shutdown can terminate it
        try:
            data_path = get_data_dir()
            pid_file = data_path / "ollama_pid.txt"
            pid_file.write_text(str(process.pid), encoding="utf-8")
        except Exception as e:
            print(f"Warning: could not write Ollama PID file: {e}")
        return process
    except Exception as e:
        print(f"Warning: Failed to start Ollama: {e}")
        return None

def wait_for_ollama(timeout=30):
    """Wait for Ollama API to be ready."""
    import requests
    print("Waiting for Ollama API...")
    sys.stdout.flush()
    for i in range(timeout):
        try:
            requests.get("http://localhost:11434", timeout=1)
            print("\nOllama is ready.")
            sys.stdout.flush()
            return True
        except requests.ConnectionError:
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(1)
    print("\nOllama did not respond within timeout.")
    return False

def launch():
    print("=" * 50)
    print("  ResKiosk Hub - Starting Up")
    print("=" * 50)
    print()
    sys.stdout.flush()
    
    base_path = get_base_path()
    data_path = get_data_dir()
    
    setup_env(base_path, data_path)
    # So admin "Restart Hub" can find TO RUN/start_hub.vbs (dev mode only; not set when frozen)
    if not getattr(sys, "frozen", False):
        os.environ["RESKIOSK_PROJECT_ROOT"] = str(base_path)
    
    # Start Ollama (non-fatal if it fails)
    ollama_proc = start_ollama(base_path)

    def _on_sigterm(*_args):
        """On SIGTERM (e.g. dashboard Turn Off), terminate Ollama and exit."""
        print("Shutting down (SIGTERM)...")
        if ollama_proc:
            try:
                ollama_proc.terminate()
                ollama_proc.wait(timeout=5)
            except Exception:
                try:
                    ollama_proc.kill()
                except Exception:
                    pass
        sys.exit(0)

    try:
        signal.signal(signal.SIGTERM, _on_sigterm)
    except (AttributeError, ValueError):
        pass  # Windows may not support SIGTERM in all contexts
    
    if ollama_proc:
        if not wait_for_ollama():
            print("Warning: Ollama failed to start. Some features may not work.")
            print("Continuing with FastAPI server anyway...")
            sys.stdout.flush()
    else:
        print("Ollama not started. Continuing without it.")
        sys.stdout.flush()
        
    print()
    print("Starting FastAPI server on http://localhost:8000 ...")
    sys.stdout.flush()
    
    # Schedule browser open
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://localhost:8000")
        
    import threading
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Import here to fail fast with clear error if something is wrong
    import uvicorn
    from hub import main
    
    try:
        hub_port = int(os.environ.get("HUB_PORT", 8000))
        uvicorn.run(main.app, host="0.0.0.0", port=hub_port, workers=1)
    finally:
        print("Shutting down...")
        if ollama_proc:
            ollama_proc.terminate()

if __name__ == "__main__":
    try:
        launch()
    except Exception as e:
        print()
        print("=" * 60)
        print("FATAL ERROR:")
        print("=" * 60)
        traceback.print_exc()
        print("=" * 60)
        print()
        input("Press Enter to exit...")
    except SystemExit as e:
        if e.code != 0:
            print()
            print(f"Hub exited with code {e.code}")
            input("Press Enter to exit...")
