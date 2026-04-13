from http.server import BaseHTTPRequestHandler
import json, os, asyncio
import httpx

DB_URL    = os.environ.get("DB_URL", "")
DB_SECRET = os.environ.get("DB_SECRET", "")
MASTER_TOKEN = os.environ.get("BOT_TOKEN", "")

async def do_broadcast(message):
    if not DB_URL or not MASTER_TOKEN:
        return 0
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.get(f"{DB_URL}/users.json?auth={DB_SECRET}&shallow=true")
            users = r.json() or {}
            count = 0
            for uid in (users if isinstance(users, dict) else {}).keys():
                ur = await c.get(f"{DB_URL}/users/{uid}/telegram_id.json?auth={DB_SECRET}")
                tid = ur.json()
                if tid:
                    await c.post(
                        f"https://api.telegram.org/bot{MASTER_TOKEN}/sendMessage",
                        json={"chat_id": tid, "text": message, "parse_mode": "HTML"}
                    )
                    count += 1
            return count
        except: return 0

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length) or b'{}')
        message = body.get("message", "")
        if not message:
            self._respond({"ok": False, "error": "نامە پێویستە"})
            return
        count = asyncio.run(do_broadcast(message))
        self._respond({"ok": True, "sent": count})

    def _respond(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass
