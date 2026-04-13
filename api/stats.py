from http.server import BaseHTTPRequestHandler
import json, os, asyncio
import sys
sys.path.insert(0, '/var/task/api')

DB_URL    = os.environ.get("DB_URL", "")
DB_SECRET = os.environ.get("DB_SECRET", "")

import httpx

async def get_stats():
    if not DB_URL:
        return {"bots": 0, "users": 0}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            rb = await c.get(f"{DB_URL}/bots.json?auth={DB_SECRET}&shallow=true")
            ru = await c.get(f"{DB_URL}/users.json?auth={DB_SECRET}&shallow=true")
            bots  = rb.json() or {}
            users = ru.json() or {}
            total_bots = sum(len(v) if isinstance(v, dict) else 0 for v in bots.values()) if isinstance(bots, dict) else 0
            return {"bots": total_bots, "users": len(users) if isinstance(users, dict) else 0}
    except:
        return {"bots": 0, "users": 0}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        stats = asyncio.run(get_stats())
        self._respond({"ok": True, **stats})

    def _respond(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass
