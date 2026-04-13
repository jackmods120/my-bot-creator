from http.server import BaseHTTPRequestHandler
import json, os, asyncio
import httpx

PROJECT_URL = os.environ.get("PROJECT_URL", "")

async def set_webhook(token):
    webhook_url = f"{PROJECT_URL}/api/bot/{token}"
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": webhook_url, "drop_pending_updates": True}
        )
        return r.json()

async def get_bot_info(token):
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.get(f"https://api.telegram.org/bot{token}/getMe")
            return r.json()
        except: return {"ok": False}

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length) or b'{}')

        token     = body.get("token", "")
        name      = body.get("name", "")
        bot_type  = body.get("type", "reaction")
        owner_uid = body.get("owner_uid", "")

        if not token or ":" not in token:
            self._respond({"ok": False, "error": "توکێن هەڵەیە"})
            return

        bot_id = token.split(":")[0]

        # Set webhook
        result = asyncio.run(set_webhook(token))

        if result.get("ok"):
            self._respond({
                "ok": True,
                "bot_id": bot_id,
                "webhook": "set"
            })
        else:
            # Even if webhook fails, return ok so app can save to Firebase
            self._respond({
                "ok": True,
                "bot_id": bot_id,
                "webhook": "failed",
                "tg_error": result.get("description", "")
            })

    def _respond(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass
