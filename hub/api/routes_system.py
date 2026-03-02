from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import asyncio
import os
import signal
import subprocess
from pathlib import Path
from hub.core.network_manager import network_manager
from hub.core.logger_stream import stream_handler

router = APIRouter()


def _get_data_dir() -> Path:
    """ResKiosk data dir (same as launcher: APPDATA/ResKiosk or parent of RESKIOSK_DB_PATH)."""
    db_path = os.environ.get("RESKIOSK_DB_PATH")
    if db_path:
        return Path(db_path).parent
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / "ResKiosk"
    return Path.home() / ".local" / "share" / "reskiosk"


def _get_project_root():
    """Project root (where TO RUN/ and hub/ live). Set by launcher in dev mode."""
    root = os.environ.get("RESKIOSK_PROJECT_ROOT")
    if root:
        return Path(root)
    return None


def _terminate_ollama_and_children():
    """Terminate Ollama process started by launcher (and any other ResKiosk-related procs)."""
    data_dir = _get_data_dir()
    pid_file = data_dir / "ollama_pid.txt"
    if not pid_file.exists():
        return
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        pid_file.unlink(missing_ok=True)
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F", "/T"],
                capture_output=True,
                timeout=5,
            )
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass
    finally:
        pid_file.unlink(missing_ok=True)

@router.get("/health")
async def health_check():
    return {"status": "ok"}


# /system/connectivity disabled (offline-first rollback)

@router.get("/admin/ping")
async def admin_ping(request: Request):
    """
    Lightweight liveness check. Also registers the kiosk via X-Kiosk-ID header.
    Per spec: every kiosk request includes X-Kiosk-ID header so the hub can
    track connected devices. This ping doubles as the heartbeat.
    """
    kiosk_id = request.headers.get("X-Kiosk-ID")
    if kiosk_id:
        client_ip = request.client.host if request.client else "unknown"
        network_manager.register_heartbeat(kiosk_id, client_ip, "online")
        print(f"[Heartbeat] Kiosk '{kiosk_id}' from {client_ip}")
    return {"status": "ok", "hub_version": "1.0"}

@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    
    # Send recent logs first
    for log in list(stream_handler.logs):
        await websocket.send_text(log)
        
    queue = asyncio.Queue()
    stream_handler.add_listener(queue)
    try:
        while True:
            # Wait for new logs
            log = await queue.get()
            await websocket.send_text(log)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WebSocket] Error in log stream: {e}")
    finally:
        stream_handler.remove_listener(queue)

@router.post("/admin/shutdown")
async def shutdown():
    """Gracefully shutdown the hub: terminate Ollama (and any ResKiosk-related procs), then this process."""
    print("[System] Shutdown requested via admin console.")

    async def _shutdown():
        await asyncio.sleep(0.5)
        _terminate_ollama_and_children()
        os.kill(os.getpid(), signal.SIGTERM)

    asyncio.create_task(_shutdown())
    return JSONResponse({"status": "ok", "message": "Hub is shutting down..."})


@router.post("/admin/restart")
async def restart():
    """
    Restart the hub: schedule TO RUN/start_hub.vbs to run after this process exits,
    then shut down (same as Turn Off). Only works when RESKIOSK_PROJECT_ROOT is set (dev mode).
    """
    project_root = _get_project_root()
    start_hub = project_root / "TO RUN" / "start_hub.vbs" if project_root else None
    if not start_hub or not start_hub.is_file():
        return JSONResponse(
            {"status": "error", "message": "Restart not available (project root or start_hub.vbs not found)."},
            status_code=503,
        )

    print("[System] Restart requested via admin console. Will shut down and start TO RUN/start_hub.vbs.")

    # Spawn a detached process that waits for this process to exit, then runs start_hub.vbs
    wait_sec = 3
    start_hub_abs = start_hub.resolve()
    if os.name == "nt":
        cmd = f'cmd /c timeout /t {wait_sec} /nobreak >nul && wscript "{start_hub_abs}"'
        creationflags = subprocess.CREATE_NO_WINDOW
        if hasattr(subprocess, "DETACHED_PROCESS"):
            creationflags |= subprocess.DETACHED_PROCESS
        subprocess.Popen(
            cmd,
            shell=True,
            cwd=str(project_root),
            creationflags=creationflags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        cmd = ["sh", "-c", f"sleep {wait_sec} && python -m hub.launcher"]
        subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    async def _shutdown():
        await asyncio.sleep(0.5)
        _terminate_ollama_and_children()
        os.kill(os.getpid(), signal.SIGTERM)

    asyncio.create_task(_shutdown())
    return JSONResponse({"status": "ok", "message": "Hub is restarting..."})
