import os
import sys
import time
import shutil
import subprocess
import tempfile
import requests
from pathlib import Path

# Avoid Windows symlink warning and related code paths when downloading to local_dir
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# -----------------------------------------------------------------------
# Configuration (paths resolved from script location so they work from any cwd)
# -----------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
HUB_MODELS_DIR = _PROJECT_ROOT / "packaging" / "hub_models"
NLLB_DIR = HUB_MODELS_DIR / "nllb"
OLLAMA_PORTABLE_DIR = _PROJECT_ROOT / "packaging" / "ollama_portable"
OLLAMA_MODELS_DIR = OLLAMA_PORTABLE_DIR / "models"

OLLAMA_FORMAT_MODEL = "translategemma:4b"
OLLAMA_REWRITE_MODEL = "llama3.2:3b"


# -----------------------------------------------------------------------
# 1.  MiniLM  (all-MiniLM-L6-v2)
# -----------------------------------------------------------------------
def bundle_minilm():
    from huggingface_hub import snapshot_download
    print("=" * 60)
    print("Bundling MiniLM-L6-v2 (sentence embedder)...")
    HUB_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        snapshot_download(
            repo_id="sentence-transformers/all-MiniLM-L6-v2",
            local_dir=str(HUB_MODELS_DIR.resolve()),
            ignore_patterns=["*.msgpack", "*.h5", "*.ot"],
        )
        print("MiniLM bundled.\n")
    except Exception as e:
        print("ERROR: Failed to download MiniLM-L6-v2 from Hugging Face.")
        print(f"Details: {e}")
        # If a previous copy already exists, allow user to proceed with it
        existing = list(HUB_MODELS_DIR.glob("*"))
        if existing:
            print(f"Existing MiniLM files found in {HUB_MODELS_DIR}.")
            print("Continuing with existing files. If embeddings fail at runtime,")
            print("please ensure Hugging Face access is allowed or manually copy")
            print("the 'sentence-transformers/all-MiniLM-L6-v2' snapshot here.")
        else:
            print("No existing MiniLM model found on disk.")
            print("Please allow Hugging Face access and re-run this script,")
            print("or manually download the model and place it under:")
            print(f"  {HUB_MODELS_DIR}")
            raise


# -----------------------------------------------------------------------
# 2.  NLLB-200 distilled 600M  (server-side translation)
# -----------------------------------------------------------------------
def bundle_nllb():
    from huggingface_hub import snapshot_download
    print("=" * 60)
    print("Bundling NLLB-200-distilled-600M (server translation)...")
    print("This is ~1.2 GB — may take a few minutes...")
    NLLB_DIR.mkdir(parents=True, exist_ok=True)
    ignore_patterns = ["*.msgpack", "*.h5", "flax_model*", "tf_model*", "rust_model*"]
    try:
        # Download to a temp cache then copy to NLLB_DIR so we always get real files
        # (avoids Windows local_dir/symlink issues that can leave the folder empty)
        with tempfile.TemporaryDirectory(prefix="reskiosk_nllb_") as tmp_cache:
            snapshot_path = snapshot_download(
                repo_id="facebook/nllb-200-distilled-600M",
                cache_dir=tmp_cache,
                ignore_patterns=ignore_patterns,
            )
            for item in Path(snapshot_path).iterdir():
                dst = NLLB_DIR / item.name
                if item.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(item, dst)
                else:
                    shutil.copy2(item, dst)
        print("NLLB-200 bundled.\n")
    except Exception as e:
        print("ERROR: Failed to download NLLB-200-distilled-600M from Hugging Face.")
        print(f"Details: {e}")
        existing = list(NLLB_DIR.glob("*"))
        if existing:
            print(f"Existing NLLB files found in {NLLB_DIR}.")
            print("Continuing with existing files. If translation fails at runtime,")
            print("please ensure Hugging Face access is allowed or manually copy")
            print("the 'facebook/nllb-200-distilled-600M' snapshot here.")
        else:
            print("No existing NLLB model found on disk.")
            print("Please allow Hugging Face access and re-run this script,")
            print("or manually download the model and place it under:")
            print(f"  {NLLB_DIR}")
            raise


# -----------------------------------------------------------------------
# 3.  Ollama setup
# -----------------------------------------------------------------------
def _find_or_copy_ollama() -> Path:
    """Locate/copy ollama.exe into the portable dir."""
    OLLAMA_PORTABLE_DIR.mkdir(parents=True, exist_ok=True)
    ollama_exe = OLLAMA_PORTABLE_DIR / "ollama.exe"

    if ollama_exe.exists():
        print("Ollama binary already present.")
        return ollama_exe

    # Try standard install location
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    installed = Path(local_appdata) / "Programs" / "Ollama" / "ollama.exe"
    if installed.exists():
        print(f"Copying installed Ollama from {installed}...")
        shutil.copy2(installed, ollama_exe)
        return ollama_exe

    # Try PATH
    which = shutil.which("ollama")
    if which:
        print(f"Copying Ollama from PATH: {which}...")
        shutil.copy2(which, ollama_exe)
        return ollama_exe

    print("WARNING: Ollama not found on this system.")
    print("To enable LLM-based formatting and direct answers, please:")
    print("  1. Install Ollama for Windows from https://ollama.com/download")
    print("  2. Ensure 'ollama.exe' is either in:")
    print("       - %LOCALAPPDATA%\\Programs\\Ollama\\ollama.exe")
    print("       - or on your PATH")
    print("  3. Re-run this script to bundle the LLM model.")
    print("Continuing without Ollama — the hub will run, but LLM features will be disabled.")
    return None


def setup_ollama():
    print("=" * 60)
    print("Setting up Ollama...")
    ollama_exe = _find_or_copy_ollama()
    return ollama_exe


def _wait_for_ollama(url="http://localhost:11434", retries=15, delay=2):
    """Wait for Ollama API to become ready."""
    for i in range(retries):
        try:
            r = requests.get(url, timeout=2)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        print(f"  Waiting for Ollama... ({i+1}/{retries})")
        time.sleep(delay)
    return False


def pull_llm_models(ollama_exe: Path):
    print("=" * 60)
    print("Pulling Ollama models:")
    print(f"  - Formatter model: {OLLAMA_FORMAT_MODEL}")
    print(f"  - Rewriter model:  {OLLAMA_REWRITE_MODEL}")
    print("This may take several minutes on first run...")

    env = os.environ.copy()
    env["OLLAMA_MODELS"] = str(OLLAMA_MODELS_DIR.absolute())

    # Start Ollama server in background
    print("Starting Ollama server...")
    server = subprocess.Popen(
        [str(ollama_exe), "serve"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )

    try:
        if not _wait_for_ollama():
            print("ERROR: Ollama server did not start in time.")
            server.terminate()
            sys.exit(1)

        for model in [OLLAMA_FORMAT_MODEL, OLLAMA_REWRITE_MODEL]:
            print(f"Pulling {model}...")
            subprocess.run(
                [str(ollama_exe), "pull", model],
                env=env,
                check=True,
            )
            print(f"{model} pulled successfully.\n")

    finally:
        print("Stopping temporary Ollama server...")
        server.terminate()
        try:
            server.wait(timeout=5)
        except Exception:
            server.kill()


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------
def main():
    bundle_minilm()
    bundle_nllb()

    # Setup and pull Ollama model if possible
    print("=" * 60)
    print("Checking for Ollama / LLM model...")
    ollama_exe = setup_ollama()
    if ollama_exe:
        try:
            pull_llm_models(ollama_exe)
        except Exception as e:
            print(f"WARNING: Failed to pull one or more Ollama models: {e}")
            print("The hub will run fine without Ollama; KB answers will just use raw text.")
    else:
        print("Ollama not found. Skipping LLM model pull.")

    print("=" * 60)
    print("Hub model bundle COMPLETE.")
    print(f"  - MiniLM:     {HUB_MODELS_DIR}")
    print(f"  - NLLB-200:   {NLLB_DIR}")
    print(f"  - Formatter model: {OLLAMA_FORMAT_MODEL} (Ollama)")
    print(f"  - Rewriter model:  {OLLAMA_REWRITE_MODEL} (Ollama)")
    print("=" * 60)


if __name__ == "__main__":
    main()
