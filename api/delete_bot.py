from http.server import BaseHTTPRequestHandler
import json, asyncio
import httpx

async def delete_webhook(token):
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.post(
                f"https://api.telegram.org/bot{token}/deleteWebhook"
            )
            return r.json()
        except: return {"ok": False}

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length) or b'{}')
        token = body.get("token", "")

        if not token:
            self._respond({"ok": False, "error": "توکێن پێویستە"})
            return

        asyncio.run(delete_webhook(token))
        # هەمیشە ok دەگەڕێنینەوە
        self._respond({"ok": True})

    def _respond(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass
