from http.server import BaseHTTPRequestHandler
import json, os, asyncio, html
import httpx

DB_URL       = os.environ.get("DB_URL", "")
DB_SECRET    = os.environ.get("DB_SECRET", "")
MASTER_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID     = 5977475208

def fb_url(path):
    return f"{DB_URL}/{path}.json?auth={DB_SECRET}"

async def db_get(path):
    if not DB_URL: return None
    async with httpx.AsyncClient(timeout=8) as c:
        try:
            r = await c.get(fb_url(path))
            return r.json() if r.status_code == 200 else None
        except: return None

async def send_tg(method, payload):
    if not MASTER_TOKEN: return {"ok": False}
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.post(f"https://api.telegram.org/bot{MASTER_TOKEN}/{method}", json=payload)
            return r.json()
        except: return {"ok": False}

async def process_master(body):
    try:
        msg = body.get("message")
        if not msg: return

        chat_id   = msg["chat"]["id"]
        txt       = msg.get("text", "")
        from_user = msg.get("from", {})
        user_id   = from_user.get("id")
        user_name = html.escape(from_user.get("first_name", "بەکارهێنەر"))

        if txt.startswith("/start"):
            # Check if blocked
            blocked = await db_get(f"blocked/{user_id}")
            if blocked:
                await send_tg("sendMessage", {
                    "chat_id": chat_id,
                    "text": "⛔ هەژمارت داخراوە."
                })
                return

            notice = await db_get("system/notice") or ""
            caption = (
                f"سڵاو، <a href='tg://user?id={user_id}'>{user_name}</a> 👋\n\n"
                f"🤖 بەخێرهاتی بۆ <b>Creator Bot</b>\n\n"
                f"دەتوانی بۆتی خۆت دروست بکەیت بە ئاسانی! 🚀\n\n"
                f"بۆتەکەت دابەزێنە و دەستپێبکە ✨"
            )
            if notice:
                caption += f"\n\n📌 <b>تێبینی:</b> {notice}"

            await send_tg("sendMessage", {
                "chat_id": chat_id,
                "text": caption,
                "parse_mode": "HTML"
            })

    except Exception as e:
        print(f"master error: {e}")


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body   = json.loads(self.rfile.read(length) or b'{}')
        asyncio.run(process_master(body))
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "active"}).encode())

    def log_message(self, format, *args):
        pass
