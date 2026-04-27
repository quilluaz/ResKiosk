import asyncio
import websockets

async def fetch_logs():
    async with websockets.connect("ws://127.0.0.1:8000/ws/logs") as ws:
        # The endpoint dumps all history synchronously before awaiting new ones
        for _ in range(200): # Just grab the first bunch of lines which is the history
            try:
                # 0.5s timeout: if we don't get anything, history is done
                msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                if "error" in msg.lower() or "exception" in msg.lower() or "[query]" in msg.lower():
                    print(msg)
            except asyncio.TimeoutError:
                break

asyncio.run(fetch_logs())
