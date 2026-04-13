from http.server import BaseHTTPRequestHandler
import json, os, asyncio, random, html
import httpx

DB_URL    = os.environ.get("DB_URL", "")
DB_SECRET = os.environ.get("DB_SECRET", "")
MASTER_TOKEN = os.environ.get("BOT_TOKEN", "")

EMOJIS = [
    "👍","👎","❤️","🔥","🥰","👏","😁","🤔","🤯","😱",
    "🤬","😢","🎉","🤩","🤮","💩","🙏","👌","🕊","🤡",
    "🥱","🥴","😍","🐳","❤️‍🔥","🌚","🌭","💯","🤣","⚡",
    "🍌","🏆","💔","🤨","😐","🍓","🍾","💋","😈",
    "😴","😭","🤓","👻","👀","🎃","🙈","😇","😂","🎄",
    "💅","🤪","🗿","🆒","💘","😎","👾","🤷","🥳",
    "🤗","🫡","🎩","🤫","😶","🌿","🤭","🤝","🦾",
    "🙃","🫠","☕","👋","🫶",
]

def fb_url(path):
    return f"{DB_URL}/{path}.json?auth={DB_SECRET}"

async def db_get(path):
    if not DB_URL: return None
    async with httpx.AsyncClient(timeout=8) as c:
        try:
            r = await c.get(fb_url(path))
            return r.json() if r.status_code == 200 else None
        except: return None

async def db_put(path, data):
    if not DB_URL: return
    async with httpx.AsyncClient(timeout=8) as c:
        try: await c.put(fb_url(path), json=data)
        except: pass

async def db_patch(path, data):
    if not DB_URL: return
    async with httpx.AsyncClient(timeout=8) as c:
        try: await c.patch(fb_url(path), json=data)
        except: pass

async def send_tg(token, method, payload):
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.post(f"https://api.telegram.org/bot{token}/{method}", json=payload)
            return r.json()
        except: return {"ok": False}

async def process_update(token, body):
    try:
        bid = token.split(":")[0]

        # ════ بۆت زانیاری لە Firebase بخوێنەوە ════
        # پێشتر لە managed_bots دەگەڕێنینەوە
        info = await db_get(f"managed_bots/{bid}")

        # ئەگەر managed_bots نەبوو، لە bots بگەڕێ
        if not info:
            # گەڕان لە هەموو بەکارهێنەران
            all_bots = await db_get("bots") or {}
            for uid_key, user_bots in (all_bots.items() if isinstance(all_bots, dict) else []):
                if isinstance(user_bots, dict) and bid in user_bots:
                    info = user_bots[bid]
                    info["owner"] = uid_key
                    break

        if not info:
            return  # بۆت نەدۆزرایەوە

        bot_type = info.get("type", "reaction")
        wlcm     = info.get("welcome_msg", "")
        bnm      = info.get("name", "Bot")

        # ════ Force Join ════
        fj      = info.get("force_join", False)
        req_chs = await db_get(f"bots/{info.get('owner','')}/{bid}/req_channels") or {}

        msg = body.get("message") or body.get("channel_post")

        # ════ Callback Query ════
        if body.get("callback_query"):
            cq      = body["callback_query"]
            cq_data = cq.get("data", "")
            cq_msg  = cq.get("message", {})
            cq_chat = cq_msg.get("chat", {}).get("id")

            await send_tg(token, "answerCallbackQuery", {"callback_query_id": cq["id"]})

            # Reaction bot settings
            if bot_type == "reaction" and cq_data.startswith("react_"):
                chat_settings = await db_get(f"bot_settings/{bid}/{cq_chat}") or {"mode": "random", "emojis": []}

                if cq_data.startswith("react_tg_"):
                    emo = cq_data.split("_")[2]
                    chat_settings["mode"] = "custom"
                    emojis = chat_settings.get("emojis", [])
                    if emo in emojis: emojis.remove(emo)
                    else: emojis.append(emo)
                    chat_settings["emojis"] = emojis
                    await db_put(f"bot_settings/{bid}/{cq_chat}", chat_settings)

                elif cq_data == "react_rnd":
                    await db_put(f"bot_settings/{bid}/{cq_chat}", {"mode": "random", "emojis": []})

                elif cq_data == "react_done":
                    async with httpx.AsyncClient(timeout=10) as c:
                        await c.post(f"https://api.telegram.org/bot{token}/deleteMessage", json={
                            "chat_id": cq_chat,
                            "message_id": cq_msg.get("message_id")
                        })

                elif cq_data == "check_join":
                    from_uid = cq.get("from", {}).get("id")
                    if from_uid:
                        not_joined = []
                        for ch in (req_chs if isinstance(req_chs, dict) else {}).keys():
                            res = await send_tg(token, "getChatMember", {"chat_id": f"@{ch}", "user_id": from_uid})
                            status = res.get("result", {}).get("status", "left")
                            if status not in ("member", "administrator", "creator"):
                                not_joined.append(ch)
                        if not_joined:
                            await send_tg(token, "answerCallbackQuery", {
                                "callback_query_id": cq["id"],
                                "text": "❌ هێشتا ئەندام نەبووی!",
                                "show_alert": True
                            })
                        else:
                            await send_tg(token, "answerCallbackQuery", {
                                "callback_query_id": cq["id"],
                                "text": "✅ سپاس! ئێستا دەتوانی بەکاری بهێنی",
                                "show_alert": True
                            })
            return

        if not msg: return

        chat_id    = msg["chat"]["id"]
        message_id = msg["message_id"]
        txt        = msg.get("text", "")
        from_user  = msg.get("from") or msg.get("sender_chat") or {}
        user_name  = html.escape(from_user.get("first_name") or from_user.get("title") or "بەکارهێنەر")
        user_id    = from_user.get("id", chat_id)

        # ════ /start Command ════
        if txt.startswith("/start"):
            # Force Join Check
            if fj and isinstance(req_chs, dict) and req_chs and from_user.get("id"):
                not_joined = []
                for ch in req_chs.keys():
                    res = await send_tg(token, "getChatMember", {"chat_id": f"@{ch}", "user_id": user_id})
                    status = res.get("result", {}).get("status", "left")
                    if status not in ("member", "administrator", "creator"):
                        not_joined.append(ch)
                if not_joined:
                    kb_rows = [[{"text": f"📢 ئەندامبوون لە @{ch}", "url": f"https://t.me/{ch}"}] for ch in not_joined]
                    kb_rows.append([{"text": "✅ پشکنینی ئەندامبوون", "callback_data": "check_join"}])
                    join_msg = "‼️ <b>تکایە سەرەتا ئەندامی کانالەکانمان بە:</b>\n\n"
                    for ch in not_joined:
                        join_msg += f"• @{ch}\n"
                    await send_tg(token, "sendMessage", {
                        "chat_id": chat_id,
                        "text": join_msg,
                        "parse_mode": "HTML",
                        "reply_markup": {"inline_keyboard": kb_rows}
                    })
                    return

            # Welcome message
            welcome = wlcm.replace("{name}", user_name) if wlcm else f"سڵاو {user_name}! 👋\n\nبەخێرهاتی بۆ <b>{html.escape(bnm)}</b>"
            await send_tg(token, "sendMessage", {
                "chat_id": chat_id,
                "text": welcome,
                "parse_mode": "HTML"
            })
            return

        # ════ Reaction Bot ════
        if bot_type == "reaction":
            chat_settings = await db_get(f"bot_settings/{bid}/{chat_id}") or {"mode": "random", "emojis": []}

            if chat_settings.get("mode") == "custom" and chat_settings.get("emojis"):
                emoji = random.choice(chat_settings["emojis"])
            else:
                emoji = random.choice(EMOJIS)

            await send_tg(token, "setMessageReaction", {
                "chat_id": chat_id,
                "message_id": message_id,
                "reaction": [{"type": "emoji", "emoji": emoji}],
                "is_big": False
            })

        # ════ /react command (reaction bot settings) ════
        if bot_type == "reaction" and txt.startswith("/react"):
            if msg["chat"]["type"] in ["group", "supergroup"]:
                cm = await send_tg(token, "getChatMember", {"chat_id": chat_id, "user_id": user_id})
                status = cm.get("result", {}).get("status", "")
                if status not in ["creator", "administrator"]:
                    return

            chat_settings = await db_get(f"bot_settings/{bid}/{chat_id}") or {"mode": "random", "emojis": []}
            keys = []
            row = []
            for e in EMOJIS[:24]:
                mark = "✅" if chat_settings.get("mode") == "custom" and e in chat_settings.get("emojis", []) else ""
                row.append({"text": f"{e}{mark}", "callback_data": f"react_tg_{e}"})
                if len(row) == 4:
                    keys.append(row)
                    row = []
            if row: keys.append(row)
            rnd_mark = "✅" if chat_settings.get("mode") == "random" else ""
            keys.append([{"text": f"🎲 هەڕەمەکی {rnd_mark}", "callback_data": "react_rnd"}])
            keys.append([{"text": "✅ پاشەکەوتکردن", "callback_data": "react_done"}])

            await send_tg(token, "sendMessage", {
                "chat_id": chat_id,
                "text": "⚙️ <b>ڕێکخستنی ڕیاکشنەکان:</b>",
                "parse_mode": "HTML",
                "reply_markup": {"inline_keyboard": keys}
            })

    except Exception as e:
        print(f"process_update error: {e}")


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # URL: /api/bot/{token}
        path  = self.path  # /api/bot/123456:ABC...
        token = path.split("/api/bot/")[-1].split("?")[0]

        length = int(self.headers.get('Content-Length', 0))
        body   = json.loads(self.rfile.read(length) or b'{}')

        if token:
            asyncio.run(process_update(token, body))

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, format, *args):
        pass
