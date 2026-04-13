import os, logging, httpx, asyncio, random, html, re, json
from datetime import datetime
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ══════════════════════════════════════════════════════════════════════════════
# ── ڕێکخستنەکان
# ══════════════════════════════════════════════════════════════════════════════
MASTER_TOKEN = os.getenv("BOT_TOKEN")
PROJECT_URL  = os.getenv("PROJECT_URL")
DB_URL       = os.getenv("DB_URL")
DB_SECRET    = os.getenv("DB_SECRET")

OWNER_ID     = 5977475208
CHANNEL_USER = "jack_721_mod"

# ══════════════════════════════════════════════════════════════════════════════
# ── CFG — ڕێکخستنەکانی گشتی
# ══════════════════════════════════════════════════════════════════════════════
CFG: dict = {
    "maintenance"  : False,
    "welcome_msg"  : "",
    "default_lang" : "ku",
    "api_timeout"  : 60,
    "vip_bypass"   : True,
    "admin_bypass" : True,
    "active_api"   : "auto",
    "total_dl"     : 0,
    "total_users"  : 0,
}

# In-memory sets (هەر request دا لە Firebase بارکردراون)
super_admins_set : set = set()
admins_set       : set = set()
blocked_set      : set = set()
vip_set          : set = set()
channels_list    : list = []
waiting_state    : dict = {}

_start_time = datetime.now()

# ══════════════════════════════════════════════════════════════════════════════
# ── سیستەمی زمان — Trilingual
# ══════════════════════════════════════════════════════════════════════════════
STRINGS: dict = {
    # ── پانێلی یەکگرتوو ──────────────────────────────────────────────────────
    "panel_header": {
        "ku": "⚙️ پانێڵی کۆنتڕۆڵ\n\n👥 بەکارهێنەران: {users}\n💎 VIP: {vip}\n🚫 بلۆككراو: {blocked}\n📥 داونلۆد: {dl}\n⏱ Uptime: {uptime}",
        "en": "⚙️ Control Panel\n\n👥 Users: {users}\n💎 VIP: {vip}\n🚫 Blocked: {blocked}\n📥 Downloads: {dl}\n⏱ Uptime: {uptime}",
        "ar": "⚙️ لوحة التحكم\n\n👥 المستخدمون: {users}\n💎 VIP: {vip}\n🚫 المحظورون: {blocked}\n📥 التنزيلات: {dl}\n⏱ وقت التشغيل: {uptime}",
    },
    # ── ئامارەکان ──────────────────────────────────────────────────────────────
    "stats": {
        "ku": "📊 ئامارەکان\n\n👥 بەکارهێنەران: {users}\n💎 VIP: {vip}\n🚫 بلۆككراو: {blocked}\n📥 داونلۆد: {dl}\n⏱ Uptime: {uptime}",
        "en": "📊 Statistics\n\n👥 Users: {users}\n💎 VIP: {vip}\n🚫 Blocked: {blocked}\n📥 Downloads: {dl}\n⏱ Uptime: {uptime}",
        "ar": "📊 الإحصائيات\n\n👥 المستخدمون: {users}\n💎 VIP: {vip}\n🚫 المحظورون: {blocked}\n📥 التنزيلات: {dl}\n⏱ وقت التشغيل: {uptime}",
    },
    # ── برۆدکاست ────────────────────────────────────────────────────────────
    "bc_ask": {
        "ku": "📢 نامەکەت بنووسە بۆ برۆدکاست:\n(هەر جۆرێک — دەق، وێنە، ڤیدیۆ)",
        "en": "📢 Write your broadcast message:\n(Any type — text, photo, video)",
        "ar": "📢 اكتب رسالة الإذاعة:\n(أي نوع — نص، صورة، فيديو)",
    },
    "bc_progress": {
        "ku": "📢 بەردەوامە... ({done}/{total})",
        "en": "📢 In progress... ({done}/{total})",
        "ar": "📢 جاري... ({done}/{total})",
    },
    "bc_done": {
        "ku": "📢 برۆدکاست تەواو بوو\n✅ گەیشت بە: {ok}\n❌ نەگەیشت: {fail}",
        "en": "📢 Broadcast complete\n✅ Reached: {ok}\n❌ Failed: {fail}",
        "ar": "📢 اكتمل الإرسال\n✅ تم الإرسال: {ok}\n❌ فشل: {fail}",
    },
    # ── بلۆک ─────────────────────────────────────────────────────────────────
    "block_ask": {
        "ku": "🚫 ئایدی بەکارهێنەرەکە بنووسە بۆ بلۆک کردن:",
        "en": "🚫 Send the user ID to block:",
        "ar": "🚫 أرسل معرف المستخدم للحظر:",
    },
    "block_done": {
        "ku": "✅ بلۆک کرا: {id}",
        "en": "✅ Blocked: {id}",
        "ar": "✅ تم الحظر: {id}",
    },
    # ── زانیاری بەکارهێنەر ────────────────────────────────────────────────────
    "userinfo_ask": {
        "ku": "👤 ئایدی بەکارهێنەرەکە بنووسە:",
        "en": "👤 Send the user ID:",
        "ar": "👤 أرسل معرف المستخدم:",
    },
    "userinfo_result": {
        "ku": "👤 زانیاری بەکارهێنەر\n\n👤 ناو: {name}\n🔗 یوزەرنەیم: @{user}\n🆔 ئایدی: {id}\n💎 VIP: {vip}\n🌍 زمان: {lang}\n📥 دابەزاندن: {dl} جار\n📅 تۆماربوون: {date}",
        "en": "👤 User Info\n\n👤 Name: {name}\n🔗 Username: @{user}\n🆔 ID: {id}\n💎 VIP: {vip}\n🌍 Language: {lang}\n📥 Downloads: {dl}\n📅 Joined: {date}",
        "ar": "👤 معلومات المستخدم\n\n👤 الاسم: {name}\n🔗 المعرف: @{user}\n🆔 ID: {id}\n💎 VIP: {vip}\n🌍 اللغة: {lang}\n📥 تنزيلات: {dl}\n📅 تاريخ الانضمام: {date}",
    },
    # ── ئەدمینەکان ─────────────────────────────────────────────────────────
    "admins_title": {
        "ku": "🛡 لیستی ئەدمینەکان ({count} ئەدمین)",
        "en": "🛡 Admin List ({count} admins)",
        "ar": "🛡 قائمة المشرفين ({count} مشرف)",
    },
    "adm_add_ask": {
        "ku": "✍️ ئایدی ئەدمینی نوێ بنووسە:",
        "en": "✍️ Send the new admin's ID:",
        "ar": "✍️ أرسل معرف المشرف الجديد:",
    },
    "adm_add_done": {
        "ku": "✅ ئەدمین کرا: {id}",
        "en": "✅ Admin added: {id}",
        "ar": "✅ تم إضافة مشرف: {id}",
    },
    "adm_rm_done": {
        "ku": "✅ ئەدمین لادرا: {id}",
        "en": "✅ Admin removed: {id}",
        "ar": "✅ تم إزالة المشرف: {id}",
    },
    "adm_rm_confirm": {
        "ku": "⚠️ دڵنیایت دەتەوێت ئەم ئەدمینە بسڕیتەوە؟\n🆔 {id}",
        "en": "⚠️ Are you sure you want to remove this admin?\n🆔 {id}",
        "ar": "⚠️ هل تريد حذف هذا المشرف؟\n🆔 {id}",
    },
    # ── VIP ────────────────────────────────────────────────────────────────
    "vips_title": {
        "ku": "💎 لیستی VIPەکان ({count} کەس)",
        "en": "💎 VIP List ({count} users)",
        "ar": "💎 قائمة VIP ({count} مستخدم)",
    },
    "vip_add_ask": {
        "ku": "✍️ ئایدی بەکارهێنەرەکە بنووسە بۆ VIP کردن:",
        "en": "✍️ Send the user ID to make VIP:",
        "ar": "✍️ أرسل معرف المستخدم لترقيته VIP:",
    },
    "vip_add_done": {
        "ku": "✅ VIP کرا: {id}",
        "en": "✅ VIP added: {id}",
        "ar": "✅ تم إضافة VIP: {id}",
    },
    "vip_rm_done": {
        "ku": "✅ VIP لادرا: {id}",
        "en": "✅ VIP removed: {id}",
        "ar": "✅ تم إزالة VIP: {id}",
    },
    # ── چەناڵەکان ────────────────────────────────────────────────────────────
    "ch_title": {
        "ku": "📢 چەناڵەکان ({count} چەناڵ)",
        "en": "📢 Channels ({count} channels)",
        "ar": "📢 القنوات ({count} قناة)",
    },
    "ch_empty": {
        "ku": "هیچ چەناڵێک نەدۆزرایەوە.",
        "en": "No channels found.",
        "ar": "لا توجد قنوات.",
    },
    "ch_add_ask": {
        "ku": "✍️ یوزەرنەیمی چەناڵ بنووسە (نمونە: @mychannel):",
        "en": "✍️ Send channel username (e.g. @mychannel):",
        "ar": "✍️ أرسل اسم القناة (مثال: @mychannel):",
    },
    "ch_add_done": {
        "ku": "✅ چەناڵ زیادکرا: {ch}",
        "en": "✅ Channel added: {ch}",
        "ar": "✅ تمت إضافة القناة: {ch}",
    },
    "ch_add_err": {
        "ku": "❌ فۆرماتی چەناڵ هەڵەیە! نمونە: @mychannel",
        "en": "❌ Wrong channel format! Example: @mychannel",
        "ar": "❌ صيغة القناة خاطئة! مثال: @mychannel",
    },
    "ch_rm_q": {
        "ku": "کام چەناڵ دەتەوێت بسڕیتەوە؟",
        "en": "Which channel do you want to remove?",
        "ar": "أي قناة تريد حذفها؟",
    },
    "ch_rm_confirm": {
        "ku": "⚠️ دڵنیایت دەتەوێت ئەم چەناڵە بسڕیتەوە؟\n{ch}",
        "en": "⚠️ Are you sure you want to remove this channel?\n{ch}",
        "ar": "⚠️ هل تريد حذف هذه القناة؟\n{ch}",
    },
    "ch_rm_done": {
        "ku": "✅ چەناڵ لادرا: {ch}",
        "en": "✅ Channel removed: {ch}",
        "ar": "✅ تمت إزالة القناة: {ch}",
    },
    # ── چاکسازی ─────────────────────────────────────────────────────────────
    "maint_on":  {"ku": "🛠 چاکسازی: چالاکە ✅",   "en": "🛠 Maintenance: Active ✅",   "ar": "🛠 الصيانة: نشط ✅"},
    "maint_off": {"ku": "🛠 چاکسازی: ناچالاکە ❌",  "en": "🛠 Maintenance: Inactive ❌", "ar": "🛠 الصيانة: غير نشط ❌"},
    "maint_msg": {
        "ku": "🛠 چاکسازی کاتی!\n\n⚙️ بۆتەکەمان لە ژێر نوێکردنەوەیەکی گەورەدایە.\n⏳ زووترین کاتێکدا دەگەڕێینەوە!\n\n📩 پەیوەندی: {dev}",
        "en": "🛠 Maintenance!\n\n⚙️ The bot is under a major update.\n⏳ We'll be back shortly!\n\n📩 Contact: {dev}",
        "ar": "🛠 صيانة!\n\n⚙️ البوت تحت تحديث كبير.\n⏳ سنعود قريباً!\n\n📩 للتواصل: {dev}",
    },
    # ── API ──────────────────────────────────────────────────────────────────
    "api_title": {
        "ku": "🔌 هەڵبژاردنی API\n\nئێستا: {act}",
        "en": "🔌 API Selection\n\nCurrent: {act}",
        "ar": "🔌 اختيار API\n\nالحالي: {act}",
    },
    # ── زمانی بۆت ────────────────────────────────────────────────────────────
    "botlang_title": {
        "ku": "🌍 زمانی سەرەکی بۆتەکە هەڵبژێرە:\n\nزمانی ئێستا: {cur}",
        "en": "🌍 Choose the bot's default language:\n\nCurrent language: {cur}",
        "ar": "🌍 اختر اللغة الافتراضية للبوت:\n\nاللغة الحالية: {cur}",
    },
    "botlang_changed": {
        "ku": "✅ زمانی سەرەکی بۆتەکە گۆڕدرا بۆ: {lang}",
        "en": "✅ Bot default language changed to: {lang}",
        "ar": "✅ تم تغيير اللغة الافتراضية إلى: {lang}",
    },
    # ── سوپەر ئەدمین ─────────────────────────────────────────────────────────
    "sup_title": {
        "ku": "🌌 لیستی سوپەر ئەدمینەکان ({count} کەس)",
        "en": "🌌 Super Admin List ({count} users)",
        "ar": "🌌 قائمة السوبر مشرفين ({count} مستخدم)",
    },
    "sup_add_ask": {
        "ku": "✍️ ئایدی سوپەر ئەدمینی نوێ بنووسە:",
        "en": "✍️ Send the new super admin's ID:",
        "ar": "✍️ أرسل معرف السوبر مشرف الجديد:",
    },
    "sup_add_done": {
        "ku": "✅ سوپەر ئەدمین کرا: {id}",
        "en": "✅ Super admin added: {id}",
        "ar": "✅ تم إضافة سوبر مشرف: {id}",
    },
    "sup_rm_confirm": {
        "ku": "⚠️ دڵنیایت دەتەوێت ئەم سوپەر ئەدمینە بسڕیتەوە؟\n🆔 {id}",
        "en": "⚠️ Are you sure you want to remove this super admin?\n🆔 {id}",
        "ar": "⚠️ هل تريد حذف هذا السوبر مشرف؟\n🆔 {id}",
    },
    "sup_rm_done": {
        "ku": "✅ سوپەر ئەدمین لادرا: {id}",
        "en": "✅ Super admin removed: {id}",
        "ar": "✅ تم إزالة السوبر مشرف: {id}",
    },
    # ── بەخێرهاتن ────────────────────────────────────────────────────────────
    "welcome_ask": {
        "ku": "✍️ نامەی بەخێرهاتن بنووسە:\n(دەتوانیت {name} و {badge} بەکاربێنیت)",
        "en": "✍️ Write the welcome message:\n(You can use {name} and {badge})",
        "ar": "✍️ اكتب رسالة الترحيب:\n(يمكنك استخدام {name} و {badge})",
    },
    "welcome_saved": {
        "ku": "✅ نامەی بەخێرهاتن گۆڕدرا.",
        "en": "✅ Welcome message updated.",
        "ar": "✅ تم تحديث رسالة الترحيب.",
    },
    # ── ڕێسەتی ئامار ─────────────────────────────────────────────────────────
    "stats_reset": {
        "ku": "✅ ئامارەکان ڕێسەت کران.",
        "en": "✅ Statistics reset successfully.",
        "ar": "✅ تم إعادة تعيين الإحصائيات.",
    },
    # ── باکئەپ ────────────────────────────────────────────────────────────────
    "backup_prep": {
        "ku": "💾 باکئەپ ئامادە دەکرێت...",
        "en": "💾 Preparing backup...",
        "ar": "💾 جاري تحضير النسخة الاحتياطية...",
    },
    # ── ئاگادارکردنەوەی بەکارهێنەری نوێ ───────────────────────────────────────
    "new_user_notif": {
        "ku": "👤 بەکارهێنەری نوێ!\n\n👤 ناو: {name}\n🔗 یوزەرنەیم: {uname}\n🆔 ئایدی: {uid}\n🌍 زمانی ئەپ: {app_lang}\n📅 کات: {date}",
        "en": "👤 New User!\n\n👤 Name: {name}\n🔗 Username: {uname}\n🆔 ID: {uid}\n🌍 App lang: {app_lang}\n📅 Date: {date}",
        "ar": "👤 مستخدم جديد!\n\n👤 الاسم: {name}\n🔗 المعرف: {uname}\n🆔 ID: {uid}\n🌍 لغة التطبيق: {app_lang}\n📅 التاريخ: {date}",
    },
    # ── دوگمەکانی گشتی ──────────────────────────────────────────────────────
    "btn_back":   {"ku": "🔙 گەڕانەوە",  "en": "🔙 Back",   "ar": "🔙 رجوع"},
    "btn_cancel": {"ku": "❌ هەڵوەشاندنەوە", "en": "❌ Cancel", "ar": "❌ إلغاء"},
    "btn_yes":    {"ku": "✅ بەڵێ",       "en": "✅ Yes",    "ar": "✅ نعم"},
    "btn_no":     {"ku": "❌ نەخێر",      "en": "❌ No",     "ar": "❌ لا"},
    "btn_refresh":{"ku": "🔄 نوێکردنەوە", "en": "🔄 Refresh", "ar": "🔄 تحديث"},
}

def get_lang(uid: int) -> str:
    """زمانی بەکارهێنەر برگەردێنێت، بە پشتیوانی CFG default"""
    return CFG.get("default_lang", "ku")

def T(uid: int, key: str, **kwargs) -> str:
    """ترجمەی string بە زمانی بەکارهێنەر"""
    lang = get_lang(uid)
    val = STRINGS.get(key, {}).get(lang) or STRINGS.get(key, {}).get("ku", key)
    return val.format(**kwargs) if kwargs else val

def uptime_str() -> str:
    delta = datetime.now() - _start_time
    h, r = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(r, 60)
    return f"{h}h {m}m {s}s"

# ══════════════════════════════════════════════════════════════════════════════
# ── پەرمیشنەکان
# ══════════════════════════════════════════════════════════════════════════════
def is_owner(uid: int) -> bool:
    return uid == OWNER_ID

def is_super(uid: int) -> bool:
    return uid == OWNER_ID or uid in super_admins_set

def is_admin_panel(uid: int) -> bool:
    return uid == OWNER_ID or uid in super_admins_set or uid in admins_set

async def load_sets_from_db():
    """لە Firebase sets بارکردن"""
    global super_admins_set, admins_set, blocked_set, vip_set, channels_list, CFG
    adms = await db_get("admins") or {}
    sups = await db_get("sys/super_admins") or {}
    blks = await db_get("blocked") or {}
    vips = await db_get("vip") or {}
    chs  = await db_get("system/req_channels") or {}
    admins_set       = set(int(k) for k in adms.keys())
    super_admins_set = set(int(k) for k in sups.keys())
    blocked_set      = set(int(k) for k in blks.keys())
    vip_set          = set(int(k) for k in vips.keys())
    channels_list    = [f"@{c}" for c in chs.keys()]
    saved_cfg = await db_get("sys/cfg") or {}
    for k, v in saved_cfg.items():
        if k in CFG:
            CFG[k] = v
EMOJIS = [
    "👍","👎","❤️","🔥","🥰","👏","😁","🤔","🤯","😱",
    "🤬","😢","🎉","🤩","🤮","💩","🙏","👌","🕊","🤡",
    "🥱","🥴","😍","🐳","❤️‍🔥","🌚","🌭","💯","🤣","⚡",
    "🍌","🏆","💔","🤨","😐","🍓","🍾","💋","🖕","😈",
    "😴","😭","🤓","👻","👨‍💻","👀","🎃","🙈","😇","😂",
    "🎅","🎄","☃️","💅","🤪","🗿","🆒","💘","🙉","🦄",
    "😘","💊","🙊","😎","👾","🤷","🦸","🥳","🥸",
    "🤗","🫡","🎩","🤫","😶","🌿","🤭","🫢","🤝","🦾",
    "🙃","🫠","☕","👋","🫶",
]
PHOTO_URL    = "https://j4ustin-03-3fc6bf0e63b7.herokuapp.com//dl/75523?code=8d9af614a362896e98ecc5c80c4b6f02f8ee81c5abe7c270"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app    = FastAPI()

# ══════════════════════════════════════════════════════════════════════════════
# ── داتابەیس
# ══════════════════════════════════════════════════════════════════════════════
def fb_url(path): return f"{DB_URL}/{path}.json?auth={DB_SECRET}"

async def db_get(path):
    if not DB_URL: return None
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.get(fb_url(path))
            return r.json() if r.status_code == 200 else None
        except: return None

async def db_put(path, data):
    if not DB_URL: return
    async with httpx.AsyncClient(timeout=10) as c:
        try: await c.put(fb_url(path), json=data)
        except: pass

async def db_patch(path, data):
    if not DB_URL: return
    async with httpx.AsyncClient(timeout=10) as c:
        try: await c.patch(fb_url(path), json=data)
        except: pass

async def db_del(path):
    if not DB_URL: return
    async with httpx.AsyncClient(timeout=10) as c:
        try: await c.delete(fb_url(path))
        except: pass

# ══════════════════════════════════════════════════════════════════════════════
# ── KEEP-ALIVE
# ══════════════════════════════════════════════════════════════════════════════
async def keep_alive_loop():
    await asyncio.sleep(30)
    while True:
        try:
            safe = (PROJECT_URL or "").rstrip('/')
            if safe:
                async with httpx.AsyncClient(timeout=15) as c:
                    await c.get(f"{safe}/ping")
                    logger.info("✅ Keep-alive")
        except Exception as e:
            logger.warning(f"Keep-alive: {e}")
        await asyncio.sleep(600)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(keep_alive_loop())
    logger.info("🚀 سێرڤەر دەستی پێکرد")

@app.get("/ping")
async def ping(): return {"ok": True, "status": "alive"}

# ══════════════════════════════════════════════════════════════════════════════
# ── یارمەتیدەر
# ══════════════════════════════════════════════════════════════════════════════
async def send_tg(token: str, method: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=12) as c:
        r = await c.post(f"https://api.telegram.org/bot{token}/{method}", json=payload)
        return r.json()

async def is_blocked(uid: int) -> bool:
    return await db_get(f"blocked/{uid}") is True

async def is_vip(uid: int) -> bool:
    data = await db_get(f"vip/{uid}")
    if not data: return False
    exp = data.get("expires", "")
    if exp == "lifetime": return True
    try: return datetime.strptime(exp, "%Y-%m-%d") >= datetime.now()
    except: return False

async def is_admin(uid: int) -> bool:
    """پشکنینی ئەیا بەکارهێنەر ئەدمینی سیستەمە"""
    if uid == OWNER_ID: return True
    admins = await db_get("admins") or {}
    return str(uid) in admins

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


async def send_and_track(update: Update, uid: int, *args, **kwargs):
    """نامەی بۆت دەنێرێت و ID ی لە لیستدا پاشەکەوت دەکات بۆ سڕینەوەی دانە دانە"""
    sent = await update.message.reply_text(*args, **kwargs)
    # زیادکردن بۆ لیستی نامەکانی بۆت
    bot_msgs = await db_get(f"users/{uid}/bot_msg_ids") or []
    if isinstance(bot_msgs, dict): bot_msgs = []
    bot_msgs.append({"msg_id": sent.message_id, "chat_id": update.message.chat_id})
    await db_put(f"users/{uid}/bot_msg_ids", bot_msgs[-50:])  # تەنها دوایین ٥٠ پاشەکەوت بکە
    return sent


async def delete_all_bot_msgs(ctx, uid: int):
    """سڕینەوەی هەموو نامەکانی بۆت کە پاشەکەوت کراون"""
    bot_msgs = await db_get(f"users/{uid}/bot_msg_ids") or []
    if isinstance(bot_msgs, dict): bot_msgs = []
    if not bot_msgs:
        return
    for item in bot_msgs:
        try:
            await ctx.bot.delete_message(chat_id=int(item["chat_id"]), message_id=int(item["msg_id"]))
        except: pass
    await db_del(f"users/{uid}/bot_msg_ids")

# ══════════════════════════════════════════════════════════════════════════════
# ── پشکنینی جۆینی ناچاری کەناڵ
# ══════════════════════════════════════════════════════════════════════════════
async def check_force_join(uid: int) -> tuple[bool, list]:
    """پشکنین ئەیا بەکارهێنەر ئەندامی هەموو کانالە داواکراوەکانە"""
    fj = await db_get("system/force_join")
    if not fj: return True, []
    req_chs = await db_get("system/req_channels") or {}
    if not req_chs: return True, []
    not_joined = []
    for ch in req_chs:
        try:
            res = await send_tg(MASTER_TOKEN, "getChatMember", {"chat_id": f"@{ch}", "user_id": uid})
            status = res.get("result", {}).get("status", "left")
            if status not in ("member", "administrator", "creator"):
                not_joined.append(ch)
        except:
            not_joined.append(ch)
    return len(not_joined) == 0, not_joined

async def send_force_join_msg(update: Update, not_joined: list):
    """ناردنی پەیامی داوای جۆین"""
    lines = ["‼️ <b>تکایە سەرەتا ئەندامی کانالەکانمان بە:</b>\n"]
    keyboard_rows = []
    for ch in not_joined:
        lines.append(f"📢 @{ch}")
        keyboard_rows.append([{"text": f"➕ ئەندامبوون لە @{ch}", "url": f"https://t.me/{ch}"}])
    keyboard_rows.append([{"text": "✅ پشکنینی ئەندامبوون", "callback_data": "check_join"}])
    msg = "\n".join(lines) + "\n\n📌 دوای ئەندامبوون، دووبارە /start بنووسە"
    await update.message.reply_text(msg, parse_mode="HTML",
        reply_markup={"inline_keyboard": keyboard_rows} if False else None)
    await update.message.reply_text(msg, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 پشکنینی دووبارە", callback_data="check_join")]]))

# ══════════════════════════════════════════════════════════════════════════════
# ██  کیبۆردەکان — هەموو InlineKeyboard
# ══════════════════════════════════════════════════════════════════════════════

def IKM(rows): return InlineKeyboardMarkup(rows)
def IKB(text, cbd): return InlineKeyboardButton(text, callback_data=cbd)
def IKU(text, url): return InlineKeyboardButton(text, url=url)

# ── مینیوی سەرەکی ──────────────────────────────────────────────────────────
def kb_main(uid: int) -> InlineKeyboardMarkup:
    rows = [
        [IKB("➕ دروستکردنی بۆتی نوێ", "mk_new"), IKB("📂 بۆتەکانم", "mk_list")],
        [IKB("📊 ئامارەکانم", "mk_stats")],
    ]
    if uid == OWNER_ID:
        rows[1] = [IKB("👑 پانێلی سەرەکی", "panel_unified"), IKB("📊 ئامارەکان", "mk_stats")]
    elif uid in admins_set or uid in super_admins_set:
        rows[1] = [IKB("⚙️ پانێلی کۆنترۆڵ", "panel_unified"), IKB("📊 ئامارەکانم", "mk_stats")]
    return IKM(rows)

def kb_main_admin(uid: int) -> InlineKeyboardMarkup:
    return IKM([
        [IKB("➕ دروستکردنی بۆتی نوێ", "mk_new"), IKB("📂 بۆتەکانم", "mk_list")],
        [IKB("⚙️ پانێلی کۆنترۆڵ", "panel_unified"), IKB("📊 ئامارەکانم", "mk_stats")],
    ])

# ── کۆنترۆڵی بۆت ─────────────────────────────────────────────────────────
def kb_control(uid: int) -> InlineKeyboardMarkup:
    rows = [
        [IKB("▶️ دەستپێکردن", "ctl_start"),    IKB("⏸ وەستاندن", "ctl_stop")],
        [IKB("🔄 نوێکردنەوە", "ctl_restart"),   IKB("📋 زانیاری بۆت", "ctl_info")],
        [IKB("✏️ گۆڕینی بەخێرهاتن", "ctl_welcome"), IKB("📨 پەیام بۆ بەکارهێنەران", "ctl_bc")],
        [IKB("🔔 چالاككردنی ئاگادار", "ctl_notif_on"), IKB("🔕 کوژاندنی ئاگادار", "ctl_notif_off")],
        [IKB("🗑 سڕینەوەی بۆت", "ctl_del"),     IKB("🔙 گەڕانەوە بۆ لیست", "mk_list")],
    ]
    if uid == OWNER_ID:
        rows.insert(4, [IKB("🔑 گۆڕینی تۆکێن", "ctl_token"), IKB("🔗 نوێکردنەوەی وەبهووک", "ctl_webhook")])
    return IKM(rows)

# ── پانێلی Owner (پانێلی سەرەکی) ─────────────────────────────────────────
def KB_OWNER_MAIN() -> InlineKeyboardMarkup:
    return IKM([
        [IKB("👥 بەشی بەکارهێنەران", "own_users"),   IKB("🤖 بەشی بۆتەکان", "own_bots")],
        [IKB("📨 بەشی پەیام", "own_msg"),             IKB("💎 بەشی VIP", "sup_vips")],
        [IKB("🛡 بەشی ئەمنیەت", "own_sec"),           IKB("📢 جۆینی ناچاری", "own_chan")],
        [IKB("⚙️ بەشی سیستەم", "own_sys"),            IKB("📊 ئامارەکان", "adm_stats")],
        [IKB("👨‍💼 بەشی ئەدمینەکان", "adm_manage_admins"), IKB("🔔 ئاگادارکردنەوە", "own_notif")],
        [IKB("🌐 جۆینی ناچاری بۆتەکان", "own_child_fj")],
        [IKB("🔙 گەڕانەوە بۆ سەرەتا", "back_home")],
    ])

# ── جۆینی ناچاری بۆ بۆتی بەکارهێنەران ───────────────────────────────────
def KB_CHILD_FJ() -> InlineKeyboardMarkup:
    return IKM([
        [IKB("➕ زیادکردنی کانال بۆ هەموو بۆتەکان", "own_child_fj_add")],
        [IKB("➖ لابردنی کانال لە هەموو بۆتەکان", "own_child_fj_del")],
        [IKB("📋 لیستی کانالەکانی جۆینی ناچاری", "own_child_fj_list")],
        [IKB("🔔 چالاككردنی جۆینی ناچاری بۆ هەموو", "own_child_fj_on")],
        [IKB("🔕 کوژاندنی جۆینی ناچاری بۆ هەموو", "own_child_fj_off")],
        [IKB("🔙 گەڕانەوە بۆ پانێلی سەرەکی", "panel_unified")],
    ])

# ── پانێلی ئاگادارکردنەوەی سەرەکی ─────────────────────────────────────────
def KB_NOTIF_MAIN() -> InlineKeyboardMarkup:
    return IKM([
        [IKB("🔔 چالاككردنی ئاگادارکردنەوەی /start", "own_notif_on")],
        [IKB("🔕 کوژاندنی ئاگادارکردنەوەی /start", "own_notif_off")],
        [IKB("📢 ئاگادارکردنەوەی بۆ بەکارهێنەرانی بۆتی سەرەکی", "own_notif_bc")],
        [IKB("🔙 گەڕانەوە بۆ سەرەتا", "back_home")],
    ])

# ── پانێلی ئەدمین ──────────────────────────────────────────────────────────
def KB_ADMIN_PANEL() -> InlineKeyboardMarkup:
    return IKM([
        [IKB("👥 لیستی بەکارهێنەران", "own_user_list"), IKB("🤖 لیستی بۆتەکان", "own_bot_list")],
        [IKB("💎 بەشی VIP", "sup_vips"),              IKB("🚫 بلۆک بەکارهێنەر", "adm_block")],
        [IKB("📨 بڵاوکردنەوە بۆ هەموو", "adm_broadcast"), IKB("🔔 ئاگادارکردنەوە", "own_notif")],
        [IKB("🔙 گەڕانەوە بۆ سەرەتا", "back_home")],
    ])

# ── بەشی ئەدمینەکان ────────────────────────────────────────────────────────
def KB_ADMINS() -> InlineKeyboardMarkup:
    return IKM([
        [IKB("👨‍💼 لیستی ئەدمینەکان", "adm_manage_admins"), IKB("➕ زیادکردنی ئەدمین", "sup_add_adm")],
        [IKB("➖ لابردنی ئەدمین", "sup_rm_adm_list"), IKB("📊 ئامارەکانی ئەدمینەکان", "own_adm_stats")],
        [IKB("🔙 گەڕانەوە بۆ پانێلی سەرەکی", "panel_unified")],
    ])

# ── بەشی ئاگادارکردنەوە ────────────────────────────────────────────────────
def KB_NOTIF() -> InlineKeyboardMarkup:
    return IKM([
        [IKB("🔔 ئاگادارکردنەوەی بەکارهێنەران", "own_notif_users")],
        [IKB("📢 ئاگادارکردنەوەی بۆتی سەرەکی", "own_notif_bc")],
        [IKB("📡 ناردنی نامە بۆ هەموو بۆتەکان", "own_notif_allbots")],
        [IKB("🔙 گەڕانەوە بۆ پانێلی سەرەکی", "panel_unified")],
    ])

def KB_NOTIF_USER() -> InlineKeyboardMarkup:
    return IKM([
        [IKB("🔔 ئاگادارکردنەوەکانم", "user_notif_on"), IKB("🔕 کوژاندنەوە", "user_notif_off")],
        [IKB("📋 مێژووی ئاگادارکردنەوە", "user_notif_hist")],
        [IKB("🔙 گەڕانەوە بۆ سەرەتا", "back_home")],
    ])

# ── بەشی بەکارهێنەران ──────────────────────────────────────────────────────
def KB_USERS() -> InlineKeyboardMarkup:
    return IKM([
        [IKB("👥 لیستی هەموو بەکارهێنەران", "own_user_list"), IKB("🔍 گەڕان بۆ بەکارهێنەر", "own_user_search")],
        [IKB("📋 زانیاری بەکارهێنەر بە ID", "adm_userinfo"), IKB("📊 ئامارەکانی بەکارهێنەران", "own_user_stats")],
        [IKB("🗑 سڕینەوەی بەکارهێنەر", "own_user_del"),     IKB("📤 هەناردەکردنی لیست", "own_user_export")],
        [IKB("🔙 گەڕانەوە بۆ پانێلی سەرەکی", "panel_unified")],
    ])

# ── بەشی بۆتەکان ───────────────────────────────────────────────────────────
def KB_BOTS() -> InlineKeyboardMarkup:
    return IKM([
        [IKB("🤖 لیستی هەموو بۆتەکان", "own_bot_list"),   IKB("🟢 بۆتە چالاکەکان", "own_bot_running")],
        [IKB("🔴 بۆتە ڕاگیراوەکان", "own_bot_stopped"),   IKB("📊 ئامارەکانی بۆتەکان", "own_bot_stats")],
        [IKB("▶️ دەستپێکردنی هەموو", "own_bot_all_start"), IKB("⏸ وەستاندنی هەموو", "own_bot_all_stop")],
        [IKB("🗑 سڕینەوەی بۆت بە ID", "own_bot_del_id"),   IKB("🔍 گەڕان بۆ بۆت", "own_bot_search")],
        [IKB("🔙 گەڕانەوە بۆ پانێلی سەرەکی", "panel_unified")],
    ])

# ── بەشی پەیام ─────────────────────────────────────────────────────────────
def KB_MSG() -> InlineKeyboardMarkup:
    return IKM([
        [IKB("📨 بڵاوکردنەوە بۆ هەموو", "own_bc_all"),    IKB("📨 بڵاوکردنەوە بۆ VIP", "own_bc_vip")],
        [IKB("📨 بڵاوکردنەوە بۆ نا-VIP", "own_bc_nonvip"), IKB("📬 پەیام بۆ بەکارهێنەرێک", "own_msg_one")],
        [IKB("📡 ناردن بۆ هەموو بۆتەکان", "own_bc_allbots"), IKB("📌 دانانی پەیامی سیستەم", "own_sys_msg_set")],
        [IKB("🗑 سڕینەوەی پەیامی سیستەم", "own_sys_msg_del"), IKB("📋 پەیامی سیستەمی ئێستا", "own_sys_msg_view")],
        [IKB("📜 مێژووی بڵاوکردنەوە", "own_bc_hist")],
        [IKB("🔙 گەڕانەوە بۆ پانێلی سەرەکی", "panel_unified")],
    ])

# ── بەشی VIP ───────────────────────────────────────────────────────────────
def KB_VIP() -> InlineKeyboardMarkup:
    return IKM([
        [IKB("💎 لیستی VIPەکان", "sup_vips"),            IKB("➕ زیادکردنی VIP", "sup_add_vip")],
        [IKB("➖ لابردنی VIP", "sup_rm_vip_list"),        IKB("📊 ئامارەکانی VIP", "own_vip_stats")],
        [IKB("💎 VIP بۆ کاتی دیاریکراو", "own_vip_date"), IKB("💎 VIP بۆ هەمیشەیی", "own_vip_life")],
        [IKB("🔍 پشکنینی VIP بەکارهێنەر", "own_vip_check"), IKB("🗑 سڕینەوەی هەموو VIP", "own_vip_del_all")],
        [IKB("🔙 گەڕانەوە بۆ پانێلی سەرەکی", "panel_unified")],
    ])

# ── بەشی ئەمنیەت ───────────────────────────────────────────────────────────
def KB_SEC() -> InlineKeyboardMarkup:
    return IKM([
        [IKB("🚫 بلۆک کردنی بەکارهێنەر", "adm_block"),    IKB("✅ لابردنی بلۆک", "own_unblock")],
        [IKB("📋 لیستی بلۆکەکان", "own_blocklist"),        IKB("🗑 سڕینەوەی هەموو بلۆک", "own_block_clear")],
        [IKB("⚠️ ئاگادارکردنەوەی بەکارهێنەر", "own_warn"), IKB("🔒 قەدەغەکردنی فیچەر", "own_restrict")],
        [IKB("🛡 مۆدی ئاگادارکردنەوە", "own_alert_mode"),  IKB("📋 لیستی ئاگادارکراوەکان", "own_warned_list")],
        [IKB("🔙 گەڕانەوە بۆ پانێلی سەرەکی", "panel_unified")],
    ])

# ── هەڵبژاردنی جۆری بۆت ──────────────────────────────────────────────────
def KB_BOT_TYPE() -> InlineKeyboardMarkup:
    return IKM([
        [IKB("🍓 بۆتی ڕیاکشن", "bt_reaction"),   IKB("🪪 بۆتی زانیاری", "bt_info")],
        [IKB("🌤️ بۆتی کەش و هەوا", "bt_weather")],
        [IKB("❌ هەڵوەشاندنەوە", "back_home")],
    ])

def KB_CHAN() -> InlineKeyboardMarkup:
    return IKM([
        [IKB("📢 گۆڕینی کانالی سەرەکی", "own_chan_main"),    IKB("🔔 چالاككردنی جۆینی ناچاری", "own_fj_on")],
        [IKB("🔕 لەکارخستنی جۆینی ناچاری", "own_fj_off"),   IKB("➕ زیادکردنی کانالی داواکراو", "own_fj_add")],
        [IKB("➖ لابردنی کانالی داواکراو", "own_fj_del"),    IKB("📋 لیستی کانالەکان", "own_fj_list")],
        [IKB("🔍 پشکنینی ئەندامی کانال", "own_fj_check"),   IKB("📊 ئامارەکانی کانال", "own_fj_stats")],
        [IKB("🗑 سڕینەوەی هەموو کانالی داواکراو", "own_fj_clear")],
        [IKB("🔙 گەڕانەوە بۆ پانێلی سەرەکی", "panel_unified")],
    ])

def KB_SYS() -> InlineKeyboardMarkup:
    return IKM([
        [IKB("⚙️ زانیاری سیستەم", "own_sys_info"),        IKB("🔄 نوێکردنەوەی هەموو وەبهووک", "own_sys_wh")],
        [IKB("🗑 پاككردنی داتابەیس", "own_sys_clear"),     IKB("💾 پشتگیری داتابەیس", "own_backup")],
        [IKB("📝 گۆڕینی بۆتی سەرەکی", "own_sys_token"),   IKB("🌐 گۆڕینی PROJECT URL", "own_sys_url")],
        [IKB("📋 لۆگەکان", "own_sys_logs"),               IKB("🔃 ڕیستارتی سیستەم", "own_sys_restart")],
        [IKB("📢 گۆڕینی کانالی بەڕێوەبەر", "own_sys_dev_ch"), IKB("🖼 گۆڕینی وێنەی بەخێرهاتن", "own_sys_photo")],
        [IKB("🔙 گەڕانەوە بۆ پانێلی سەرەکی", "panel_unified")],
    ])

# ══════════════════════════════════════════════════════════════════════════════
# ██  /start
# ══════════════════════════════════════════════════════════════════════════════
async def master_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    name = html.escape(update.effective_user.first_name or "بەکارهێنەر")

    if await is_blocked(uid):
        await update.message.reply_text("🚫 دەستت لە بۆتەکە گرتراوە.")
        return

    # پشکنینی جۆینی ناچاری کەناڵ بۆ بەکارهێنەرانی ئاسایی
    if uid != OWNER_ID and not await is_admin(uid):
        joined, not_joined = await check_force_join(uid)
        if not joined:
            await send_force_join_msg(update, not_joined)
            return

    await db_del(f"users/{uid}/state")
    await db_patch(f"users/{uid}", {
        "name":     update.effective_user.first_name or "",
        "username": update.effective_user.username   or "",
        "active":   True,
        "last_seen": now_str(),
    })

    vip_badge   = " 💎" if await is_vip(uid) else ""
    admin_badge = " 🛡" if (await is_admin(uid) and uid != OWNER_ID) else ""
    R = "\u200f"

    if uid == OWNER_ID:
        all_b  = await db_get("managed_bots") or {}
        all_u  = await db_get("users")         or {}
        run    = sum(1 for v in all_b.values() if v.get("status") == "running")
        admins = await db_get("admins")        or {}
        txt = (
            f"{R}‼️ <b>بەخێربێیت خاوەنی سیستەم، {name}!</b>\n\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}👥 بەکارهێنەران: <b>{len(all_u)}</b>\n"
            f"{R}🤖 بۆتەکان: <b>{len(all_b)}</b>  (🟢{run}  🔴{len(all_b)-run})\n"
            f"{R}👨\u200d💼 ئەدمینەکان: <b>{len(admins)}</b>\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}🎛 پانێلی سەرەکی — کۆنترۆڵی تەواوی سیستەم\n"
            f"{R}👇 هەڵبژاردنێک بکە:"
        )
        sent = await send_and_track(update, uid, txt, parse_mode="HTML", reply_markup=kb_main(uid))
    elif await is_admin(uid):
        txt = (
            f"{R}‼️ <b>بەخێربێیت، ئەدمین {name}{admin_badge}!</b>\n\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}🛡 دەستتە بۆ پانێلی ئەدمین\n"
            f"{R}🤖 دروستکردنی بۆتی تایبەتی خۆت\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}👇 هەڵبژاردنێک بکە:"
        )
        sent = await send_and_track(update, uid, txt, parse_mode="HTML", reply_markup=kb_main_admin(uid))
    else:
        vip_speed = "⚡ خێرا" if await is_vip(uid) else "🐢 ئاسایی"
        txt = (
            f"{R}‼️ <b>بەخێربێیت، {name}{vip_badge}!</b>\n\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}🤖 دروستکردنی بۆتی تایبەتی خۆت\n"
            f"{R}⚙️ کۆنترۆڵی تەواوی بۆتەکەت\n"
            f"{R}📨 ناردنی پەیام بۆ بەکارهێنەرانی بۆتەکەت\n"
            f"{R}🚀 خێرایی: {vip_speed}\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}👇 هەڵبژاردنێک بکە:"
        )
        sent = await send_and_track(update, uid, txt, parse_mode="HTML", reply_markup=kb_main(uid))

# ══════════════════════════════════════════════════════════════════════════════
# ██  handler ی سەرەکی
# ══════════════════════════════════════════════════════════════════════════════
async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt   = update.message.text.strip()
    uid   = update.effective_user.id
    state = await db_get(f"users/{uid}/state") or ""

    if await is_blocked(uid):
        await update.message.reply_text("🚫 دەستت لە بۆتەکە گرتراوە.")
        return

    # ── سڕینەوەی هەموو نامەکانی بۆت (دانە دانە) ─────────────────────────
    await delete_all_bot_msgs(ctx, uid)
    if txt == "🔄 پشکنینی دووبارە":
        if uid != OWNER_ID and not await is_admin(uid):
            joined, not_joined = await check_force_join(uid)
            if not joined:
                await send_force_join_msg(update, not_joined)
            else:
                await master_start(update, ctx)
        else:
            await master_start(update, ctx)
        return

    # ── ناڤیگەیشنی گشتی ───────────────────────────────────────────────────
    if txt == "🔙 گەڕانەوە بۆ سەرەتا":
        await db_del(f"users/{uid}/state")
        await master_start(update, ctx)
        return

    if txt == "🔙 گەڕانەوە بۆ لیست":
        await db_del(f"users/{uid}/state")
        await show_bot_list(update, uid)
        return

    if txt == "🔙 گەڕانەوە بۆ پانێلی سەرەکی" and uid == OWNER_ID:
        await db_del(f"users/{uid}/state")
        await show_owner_main(update)
        return

    if txt == "🔙 گەڕانەوە بۆ پانێلی سەرەکی" and await is_admin(uid):
        await db_del(f"users/{uid}/state")
        await update.message.reply_text("🛡 پانێلی ئەدمین:", reply_markup=KB_ADMIN_PANEL())
        return

    # ── دروستکردنی بۆتی نوێ ───────────────────────────────────────────────
    if txt == "➕ دروستکردنی بۆتی نوێ":
        # پشکنینی جۆینی ناچاری کەناڵ
        if uid != OWNER_ID and not await is_admin(uid):
            joined, not_joined = await check_force_join(uid)
            if not joined:
                await send_force_join_msg(update, not_joined)
                return
        R = "\u200f"
        await db_put(f"users/{uid}/state", "choose_bot_type")
        await update.message.reply_text(
            f"{R}🤖 <b>جۆری بۆتەکەت هەڵبژێرە</b>",
            parse_mode="HTML", reply_markup=KB_BOT_TYPE(),
        )
        return

    if txt == "🍓 بۆتی ڕیاکشن":
        await db_put(f"users/{uid}/state", "await_token")
        await db_put(f"users/{uid}/pending_bot_type", "reaction")
        R = "\u200f"
        kb = IKM([[IKB("🔙 گەڕانەوە بۆ سەرەتا", "back_home")]])
        await update.message.reply_text(
            f"{R}🍓 <b>دروستکردنی بۆتی ڕیاکشن</b>\n\n"
            f"{R}📋 <b>مامەڵەکە:</b>\n"
            f"{R}١. بچۆ بۆ @BotFather لە تێلیگرام\n"
            f"{R}٢. بنووسە /newbot\n"
            f"{R}٣. ناوی بۆتەکەت دابنێ\n"
            f"{R}٤. تۆکێنەکەی کۆپی بکە و لێرە بینێرە\n\n"
            f"{R}⬇️ <b>تۆکێنەکەت لێرە بینێرە:</b>",
            parse_mode="HTML", reply_markup=kb,
        )
        return

    if txt == "🌤️ بۆتی کەش و هەوا":
        await db_put(f"users/{uid}/state", "await_token")
        await db_put(f"users/{uid}/pending_bot_type", "weather")
        R = "\u200f"
        kb = IKM([[IKB("🔙 گەڕانەوە بۆ سەرەتا", "back_home")]])
        await update.message.reply_text(
            f"{R}🌤️ <b>دروستکردنی بۆتی کەش و هەوا</b>\n\n"
            f"{R}📋 <b>مامەڵەکە:</b>\n"
            f"{R}١. بچۆ بۆ @BotFather لە تێلیگرام\n"
            f"{R}٢. بنووسە /newbot\n"
            f"{R}٣. ناوی بۆتەکەت دابنێ\n"
            f"{R}٤. تۆکێنەکەی کۆپی بکە و لێرە بینێرە\n\n"
            f"{R}⬇️ <b>تۆکێنەکەت لێرە بینێرە:</b>",
            parse_mode="HTML", reply_markup=kb,
        )
        return

    if txt == "🪪 بۆتی زانیاری":
        await db_put(f"users/{uid}/state", "await_token")
        await db_put(f"users/{uid}/pending_bot_type", "info")
        R = "\u200f"
        kb = IKM([[IKB("🔙 گەڕانەوە بۆ سەرەتا", "back_home")]])
        await update.message.reply_text(
            f"{R}🪪 <b>دروستکردنی بۆتی زانیاری</b>\n\n"
            f"{R}📋 <b>مامەڵەکە:</b>\n"
            f"{R}١. بچۆ بۆ @BotFather لە تێلیگرام\n"
            f"{R}٢. بنووسە /newbot\n"
            f"{R}٣. ناوی بۆتەکەت دابنێ\n"
            f"{R}٤. تۆکێنەکەی کۆپی بکە و لێرە بینێرە\n\n"
            f"{R}⬇️ <b>تۆکێنەکەت لێرە بینێرە:</b>",
            parse_mode="HTML", reply_markup=kb,
        )
        return

    # ── لیستی بۆتەکانم ────────────────────────────────────────────────────
    if txt == "📂 بۆتەکانم":
        await show_bot_list(update, uid)
        return

    # ── هەڵبژاردنی بۆت ───────────────────────────────────────────────────
    if re.match(r"^[🟢🔴⚪].+@\S+$", txt):
        uname = re.sub(r"^.*@", "", txt).strip()
        all_b = await db_get("managed_bots") or {}
        bid   = next((k for k, v in all_b.items()
                      if v.get("owner") == uid and v.get("bot_username") == uname), None)
        if not bid:
            await update.message.reply_text("❌ بۆتەکە نەدۆزرایەوە!", reply_markup=kb_main(uid))
            return
        await db_put(f"users/{uid}/selected_bot", bid)
        await show_bot_control(update, uid, bid, all_b[bid])
        return

    # ── کوژاندنی/چالاككردنی ئاگادارکردنەوەی بۆت ─────────────────────────
    if txt == "🔕 کوژاندنی ئاگادارکردنەوەی بۆتم":
        R = "\u200f"
        all_b = await db_get("managed_bots") or {}
        mine  = {k:v for k,v in all_b.items() if v.get("owner") == uid}
        for bid_k, binfo in mine.items():
            binfo["notif_enabled"] = False
            await db_put(f"managed_bots/{bid_k}", binfo)
        kb_on = IKM([[IKB("📂 بۆتەکانم", "mk_list"), IKB("🔔 چالاككردن", "ctl_notif_on")], [IKB("🔙 گەڕانەوە بۆ سەرەتا", "back_home")]])
        await update.message.reply_text(
            f"{R}🔕 <b>ئاگادارکردنەوەی بۆتەکانت کوژێنرایەوە</b>\n\n"
            f"{R}📌 ئێستا کاتێک بەکارهێنەرێک /start کرد ئاگادار ناکرێیتەوە",
            parse_mode="HTML", reply_markup=kb_on
        )
        return

    if txt == "🔔 چالاككردنی ئاگادارکردنەوەی بۆتم":
        R = "\u200f"
        all_b = await db_get("managed_bots") or {}
        mine  = {k:v for k,v in all_b.items() if v.get("owner") == uid}
        for bid_k, binfo in mine.items():
            binfo["notif_enabled"] = True
            await db_put(f"managed_bots/{bid_k}", binfo)
        kb_off = IKM([[IKB("📂 بۆتەکانم", "mk_list"), IKB("🔕 کوژاندن", "ctl_notif_off")], [IKB("🔙 گەڕانەوە بۆ سەرەتا", "back_home")]])
        await update.message.reply_text(
            f"{R}🔔 <b>ئاگادارکردنەوەی بۆتەکانت چالاک کرایەوە</b>\n\n"
            f"{R}📌 ئێستا کاتێک بەکارهێنەرێک /start کرد ئاگادار دەکرێیتەوە 🔔",
            parse_mode="HTML", reply_markup=kb_off
        )
        return

    # ── دوگمەکانی کۆنترۆڵ ────────────────────────────────────────────────
    CTRL = {
        "▶️ دەستپێکردن","⏸ وەستاندن","🔄 نوێکردنەوە","📋 زانیاری بۆت",
        "✏️ گۆڕینی بەخێرهاتن","📨 پەیام بۆ بەکارهێنەران",
        "🗑 سڕینەوەی بۆت","🔑 گۆڕینی تۆکێن","🔗 نوێکردنەوەی وەبهووک",
    }
    if txt in CTRL:
        await handle_control(update, uid, txt)
        return

    # ── ئاگادارکردنەوەی /start بۆ بۆتی دیاریکراو ────────────────────────
    if txt in ("🔔 ئاگادارکردنەوەی /start", "🔕 کوژاندنی ئاگادارکردنەوە"):
        R = "\u200f"
        bid = await db_get(f"users/{uid}/selected_bot")
        if not bid:
            await update.message.reply_text(f"{R}❌ پێشەکی بۆتێک هەڵبژێرە.", reply_markup=kb_main(uid))
            return
        binfo = await db_get(f"managed_bots/{bid}") or {}
        enable = (txt == "🔔 ئاگادارکردنەوەی /start")
        binfo["notif_enabled"] = enable
        await db_put(f"managed_bots/{bid}", binfo)
        bun = binfo.get("bot_username", "بۆت")
        if enable:
            await update.message.reply_text(
                f"{R}🔔 <b>ئاگادارکردنەوەی /start چالاک کرا</b>\n\n"
                f"{R}🤖 بۆت: @{bun}\n"
                f"{R}📌 ئێستا کاتێک بەکارهێنەرێک یەکەم جار /start کرد ئاگادار دەکرێیتەوە",
                parse_mode="HTML", reply_markup=kb_control(uid)
            )
        else:
            await update.message.reply_text(
                f"{R}🔕 <b>ئاگادارکردنەوەی /start کوژێنرایەوە</b>\n\n"
                f"{R}🤖 بۆت: @{bun}\n"
                f"{R}📌 ئاگادارکردنەوە بۆ ئەم بۆتە کوژێنرایەوە",
                parse_mode="HTML", reply_markup=kb_control(uid)
            )
        return

    # ── ئامار ─────────────────────────────────────────────────────────────
    if txt in ("📊 ئامارەکان","📊 ئامارەکانم"):
        await show_stats(update, uid)
        return

    # ── پانێلی ئەدمین (بۆ ئەدمینەکان) ───────────────────────────────────
    if txt == "🛡 پانێلی ئەدمین" and await is_admin(uid) and uid != OWNER_ID:
        await update.message.reply_text("🛡 <b>پانێلی ئەدمین</b>\n\nهەڵبژاردنێک بکە:", parse_mode="HTML", reply_markup=KB_ADMIN_PANEL())
        return

    # ── بەشی ئاگادارکردنەوە (بۆ بەکارهێنەران) ──────────────────────────
    if txt == "🔔 ئاگادارکردنەوەکانم":
        await show_user_notifications(update, uid)
        return

    # ════════════════════════════════════════════════════════════════════════
    # پانێلی سەرەکی و بەشەکانی (تەنها Owner)
    # ════════════════════════════════════════════════════════════════════════
    if uid == OWNER_ID:
        # ── مینیوی سەرەکی ─────────────────────────────────────────────────
        if txt == "👑 پانێلی سەرەکی":
            await show_owner_main(update)
            return

        # ════ بەشی بەکارهێنەران ════════════════════════════════════════════
        if txt == "👥 بەشی بەکارهێنەران":
            await update.message.reply_text("👥 <b>بەشی بەکارهێنەران</b>\n\nهەڵبژاردنێک بکە:", parse_mode="HTML", reply_markup=KB_USERS())
            return
        if txt == "👥 لیستی هەموو بەکارهێنەران":
            await owner_list_users(update, full=True)
            return
        if txt == "🔍 گەڕان بۆ بەکارهێنەر":
            await db_put(f"users/{uid}/state", "search_user")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🔍 ناو یان یوزەرنەیم یان ID ی بەکارهێنەرەکە بنووسە:", reply_markup=kb)
            return
        if txt == "📋 زانیاری بەکارهێنەر بە ID":
            await db_put(f"users/{uid}/state", "user_info_id")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🆔 ID ی بەکارهێنەرەکە بنووسە:", reply_markup=kb)
            return
        if txt == "📊 ئامارەکانی بەکارهێنەران":
            await owner_user_stats(update)
            return
        if txt == "🗑 سڕینەوەی بەکارهێنەر":
            await db_put(f"users/{uid}/state", "del_user")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🆔 ID ی بەکارهێنەرەکە بنووسە تا بیسڕیتەوە:", reply_markup=kb)
            return
        if txt == "📤 هەناردەکردنی لیست":
            await owner_export_users(update)
            return

        # ════ بەشی بۆتەکان ════════════════════════════════════════════════
        if txt == "🤖 بەشی بۆتەکان":
            await update.message.reply_text("🤖 <b>بەشی بۆتەکان</b>\n\nهەڵبژاردنێک بکە:", parse_mode="HTML", reply_markup=KB_BOTS())
            return
        if txt == "🤖 لیستی هەموو بۆتەکان":
            await owner_list_bots(update, filter_status=None)
            return
        if txt == "🟢 بۆتە چالاکەکان":
            await owner_list_bots(update, filter_status="running")
            return
        if txt == "🔴 بۆتە ڕاگیراوەکان":
            await owner_list_bots(update, filter_status="stopped")
            return
        if txt == "📊 ئامارەکانی بۆتەکان":
            await owner_bot_stats(update)
            return
        if txt == "▶️ دەستپێکردنی هەموو":
            await owner_all_bots_action(update, "running")
            return
        if txt == "⏸ وەستاندنی هەموو":
            await owner_all_bots_action(update, "stopped")
            return
        if txt == "🗑 سڕینەوەی بۆت بە ID":
            await db_put(f"users/{uid}/state", "owner_del_bot")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🆔 ID ی بۆتەکە بنووسە:", reply_markup=kb)
            return
        if txt == "🔍 گەڕان بۆ بۆت":
            await db_put(f"users/{uid}/state", "search_bot")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🔍 یوزەرنەیم یان ID ی بۆتەکە بنووسە:", reply_markup=kb)
            return

        # ════ بەشی پەیام ══════════════════════════════════════════════════
        if txt == "📨 بەشی پەیام":
            await update.message.reply_text("📨 <b>بەشی پەیام</b>\n\nهەڵبژاردنێک بکە:", parse_mode="HTML", reply_markup=KB_MSG())
            return
        if txt == "📨 بڵاوکردنەوە بۆ هەموو":
            await db_put(f"users/{uid}/state", "bc_all")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("📨 <b>بڵاوکردنەوە بۆ هەموو</b>\n\nپەیامەکەت بنووسە:", parse_mode="HTML", reply_markup=kb)
            return
        if txt == "📨 بڵاوکردنەوە بۆ VIP":
            await db_put(f"users/{uid}/state", "bc_vip")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("💎 <b>بڵاوکردنەوە بۆ VIPەکان تەنها</b>\n\nپەیامەکەت بنووسە:", parse_mode="HTML", reply_markup=kb)
            return
        if txt == "📨 بڵاوکردنەوە بۆ نا-VIP":
            await db_put(f"users/{uid}/state", "bc_nonvip")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("📨 <b>بڵاوکردنەوە بۆ نا-VIPەکان</b>\n\nپەیامەکەت بنووسە:", parse_mode="HTML", reply_markup=kb)
            return
        if txt == "📬 پەیام بۆ بەکارهێنەرێک":
            await db_put(f"users/{uid}/state", "msg_one_id")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🆔 ID ی بەکارهێنەرەکە بنووسە:", reply_markup=kb)
            return
        if txt == "📡 ناردن بۆ هەموو بۆتەکان":
            # کۆکردنەوەی هەموو بەکارهێنەرانی هەموو بۆتەکان (بەبێ دووبارەکردن)
            all_b = await db_get("managed_bots") or {}
            R = "\u200f"
            # ژمارەکردنی کۆی بەکارهێنەران لە هەموو بۆتەکاندا
            bot_user_map: dict = {}  # bid -> list of (user_id, token)
            total_unique = set()
            for bid_k, binfo in all_b.items():
                token_k = binfo.get("token","")
                if not token_k: continue
                bu = await db_get(f"bot_users/{bid_k}") or {}
                if bu:
                    bot_user_map[bid_k] = {"token": token_k, "users": list(bu.keys()), "name": binfo.get("bot_username","—")}
                    total_unique.update(bu.keys())
            if not bot_user_map:
                await update.message.reply_text(f"{R}📭 هیچ بەکارهێنەرێک لە بۆتەکاندا نییە.", reply_markup=KB_MSG())
                return
            await db_put(f"users/{uid}/state", "bc_all_child_bots")
            # پاشەکەوتکردنی نەخشەکە بۆ بەکارهێنان لە state
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text(
                f"{R}📡 <b>ناردن بۆ هەموو بۆتەکان</b>\n"
                f"{R}━━━━━━━━━━━━━━━━━━━\n"
                f"{R}🤖 ژمارەی بۆتەکان: <b>{len(bot_user_map)}</b>\n"
                f"{R}👥 کۆی بەکارهێنەران: <b>{len(total_unique)}</b> کەس\n"
                f"{R}━━━━━━━━━━━━━━━━━━━\n"
                f"{R}⬇️ پەیامەکەت بنووسە، دەچێت بۆ هەموو بەکارهێنەران لە هەموو بۆتەکاندا:",
                parse_mode="HTML", reply_markup=kb
            )
            return
        if txt == "📌 دانانی پەیامی سیستەم":
            await db_put(f"users/{uid}/state", "set_sys_msg")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text(
                "📌 <b>دانانی پەیامی سیستەم</b>\n\n"
                "ئەم پەیامە بە هەموو بەکارهێنەرانەوە نیشاندەدرێت کاتێک دەستی پێدەکەن.\n"
                "پەیامەکەت بنووسە (HTML پشتگیری دەکات):",
                parse_mode="HTML", reply_markup=kb,
            )
            return
        if txt == "🗑 سڕینەوەی پەیامی سیستەم":
            await db_del("system/notice")
            await update.message.reply_text("✅ پەیامی سیستەم سڕایەوە.", reply_markup=KB_MSG())
            return
        if txt == "📋 پەیامی سیستەمی ئێستا":
            msg_now = await db_get("system/notice")
            if msg_now:
                await update.message.reply_text(f"📌 <b>پەیامی سیستەمی ئێستا:</b>\n\n{msg_now}", parse_mode="HTML", reply_markup=KB_MSG())
            else:
                await update.message.reply_text("📭 هیچ پەیامی سیستەمێک دانەنراوە.", reply_markup=KB_MSG())
            return
        if txt == "📜 مێژووی بڵاوکردنەوە":
            await owner_broadcast_history(update)
            return

        # ════ بەشی VIP ════════════════════════════════════════════════════
        if txt == "💎 بەشی VIP":
            await update.message.reply_text("💎 <b>بەشی VIP</b>\n\nهەڵبژاردنێک بکە:", parse_mode="HTML", reply_markup=KB_VIP())
            return
        if txt == "💎 لیستی VIPەکان":
            await owner_list_vips(update)
            return
        if txt == "➕ زیادکردنی VIP":
            await db_put(f"users/{uid}/state", "add_vip")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🆔 ID ی بەکارهێنەرەکە بنووسە:", reply_markup=kb)
            return
        if txt == "➖ لابردنی VIP":
            await db_put(f"users/{uid}/state", "del_vip")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🆔 ID ی VIP بنووسە:", reply_markup=kb)
            return
        if txt == "📊 ئامارەکانی VIP":
            await owner_vip_stats(update)
            return
        if txt == "💎 VIP بۆ کاتی دیاریکراو":
            await db_put(f"users/{uid}/state", "add_vip_date")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🆔 ID ی بەکارهێنەر بنووسە، ئینجا بەرواری بەسەرچوون:\nنموونە: <code>123456789 2025-12-31</code>", parse_mode="HTML", reply_markup=kb)
            return
        if txt == "💎 VIP بۆ هەمیشەیی":
            await db_put(f"users/{uid}/state", "add_vip_life")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🆔 ID ی بەکارهێنەر بنووسە (VIP بۆ هەمیشە دەبێت):", reply_markup=kb)
            return
        if txt == "🔍 پشکنینی VIP بەکارهێنەر":
            await db_put(f"users/{uid}/state", "check_vip")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🆔 ID ی بەکارهێنەر بنووسە:", reply_markup=kb)
            return
        if txt == "🗑 سڕینەوەی هەموو VIP":
            await db_put(f"users/{uid}/state", "confirm_del_all_vip")
            kb = IKM([[IKB("✅ بەڵێ، هەموو VIP بسڕەوە", "own_vip_del_all_yes")], [IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("⚠️ <b>دڵنیایت؟</b> هەموو VIPەکان دەسڕیتەوە!", parse_mode="HTML", reply_markup=kb)
            return

        # ════ بەشی ئەمنیەت ════════════════════════════════════════════════
        if txt == "🛡 بەشی ئەمنیەت":
            await update.message.reply_text("🛡 <b>بەشی ئەمنیەت</b>\n\nهەڵبژاردنێک بکە:", parse_mode="HTML", reply_markup=KB_SEC())
            return
        if txt == "🚫 بلۆک کردنی بەکارهێنەر":
            await db_put(f"users/{uid}/state", "block_user")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🆔 ID ی بەکارهێنەرەکە بنووسە:", reply_markup=kb)
            return
        if txt == "✅ لابردنی بلۆک":
            await db_put(f"users/{uid}/state", "unblock_user")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🆔 ID ی بەکارهێنەرەکە بنووسە:", reply_markup=kb)
            return
        if txt == "📋 لیستی بلۆکەکان":
            await owner_list_blocked(update)
            return
        if txt == "🗑 سڕینەوەی هەموو بلۆک":
            await db_del("blocked")
            await update.message.reply_text("✅ هەموو بلۆکەکان سڕایەوە.", reply_markup=KB_SEC())
            return
        if txt == "⚠️ ئاگادارکردنەوەی بەکارهێنەر":
            await db_put(f"users/{uid}/state", "warn_user_id")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🆔 ID ی بەکارهێنەر بنووسە:", reply_markup=kb)
            return
        if txt == "🔒 قەدەغەکردنی فیچەر":
            await db_put(f"users/{uid}/state", "restrict_feat")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text(
                "🔒 ناوی فیچەر بنووسە کە دەتەوێت قەدەغە بکەیت:\n"
                "نموونە: <code>create_bot</code> یان <code>broadcast</code>",
                parse_mode="HTML", reply_markup=kb,
            )
            return
        if txt == "🛡 مۆدی ئاگادارکردنەوە":
            await owner_toggle_alert_mode(update, uid)
            return
        if txt == "📋 لیستی ئاگادارکراوەکان":
            await owner_list_warned(update)
            return

        # ════ بەشی کانال ══════════════════════════════════════════════════
        if txt == "📢 جۆینی ناچاری":
            fj = await db_get("system/force_join") or False
            req_chs = await db_get("system/req_channels") or {}
            await update.message.reply_text(
                f"📢 <b>بەشی جۆینی ناچاری</b>\n\n"
                f"📋 کانالە داواکراوەکان: <b>{len(req_chs)}</b>\n"
                f"🔔 دۆخ: <b>{'✅ چالاک' if fj else '❌ لەکارخراو'}</b>\n\n"
                "هەڵبژاردنێک بکە:",
                parse_mode="HTML", reply_markup=KB_CHAN()
            )
            return
        if txt == "📢 گۆڕینی کانالی سەرەکی":
            await db_put(f"users/{uid}/state", "change_main_channel")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("📢 یوزەرنەیمی کانالی نوێ بنووسە (بەبێ @):", reply_markup=kb)
            return
        if txt == "🔔 چالاككردنی جۆینی ناچاری":
            await db_put("system/force_join", True)
            await update.message.reply_text("✅ جۆینی ناچاری چالاک کرا!\n\nئێستا بەکارهێنەران پێش بەکارهێنانی بۆت دەبێت ئەندامی کانالەکان بن.", reply_markup=KB_CHAN())
            return
        if txt == "🔕 لەکارخستنی جۆینی ناچاری":
            await db_put("system/force_join", False)
            await update.message.reply_text("❌ جۆینی ناچاری لەکارخرا.", reply_markup=KB_CHAN())
            return
        if txt == "➕ زیادکردنی کانالی داواکراو":
            await db_put(f"users/{uid}/state", "add_req_channel")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text(
                "➕ یوزەرنەیمی کانالەکە بنووسە (بەبێ @):\n\n"
                "💡 تێبینی: بۆتی سەرەکی دەبێت ئەدمینی ئەم کانالە بێت",
                reply_markup=kb,
            )
            return
        if txt == "➖ لابردنی کانالی داواکراو":
            await db_put(f"users/{uid}/state", "del_req_channel")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("➖ یوزەرنەیمی کانالەکە بنووسە (بەبێ @):", reply_markup=kb)
            return
        if txt == "📋 لیستی کانالەکان":
            await owner_list_channels(update)
            return
        if txt == "🗑 سڕینەوەی هەموو کانالی داواکراو":
            await db_del("system/req_channels")
            await update.message.reply_text("🗑 هەموو کانالە داواکراوەکان سڕایەوە.", reply_markup=KB_CHAN())
            return
        if txt == "🔍 پشکنینی ئەندامی کانال":
            await db_put(f"users/{uid}/state", "check_member")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🆔 ID ی بەکارهێنەر بنووسە:", reply_markup=kb)
            return
        if txt == "📊 ئامارەکانی کانال":
            await owner_channel_stats(update)
            return

        # ════ بەشی ئەدمینەکان ═════════════════════════════════════════════
        if txt == "👨‍💼 بەشی ئەدمینەکان":
            await update.message.reply_text("👨‍💼 <b>بەشی ئەدمینەکان</b>\n\nهەڵبژاردنێک بکە:", parse_mode="HTML", reply_markup=KB_ADMINS())
            return
        if txt == "👨‍💼 لیستی ئەدمینەکان":
            await owner_list_admins(update)
            return
        if txt == "➕ زیادکردنی ئەدمین":
            await db_put(f"users/{uid}/state", "add_admin")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text(
                "👨‍💼 <b>زیادکردنی ئەدمینی نوێ</b>\n\n"
                "🆔 ID ی بەکارهێنەرەکە بنووسە کە دەتەوێت ئەدمینی بکەیت:",
                parse_mode="HTML", reply_markup=kb,
            )
            return
        if txt == "➖ لابردنی ئەدمین":
            await db_put(f"users/{uid}/state", "del_admin")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🆔 ID ی ئەدمینەکە بنووسە تا لابیبریت:", reply_markup=kb)
            return
        if txt == "📊 ئامارەکانی ئەدمینەکان":
            await owner_admin_stats(update)
            return

        # ════ بەشی ئاگادارکردنەوە ═════════════════════════════════════════
        if txt == "🔔 بەشی ئاگادارکردنەوە":
            R = "\u200f"
            # ئامارەکانی ئاگادارکردنەوە بۆ هەموو بۆتەکانی ئەم بەکارهێنەرە
            all_b = await db_get("managed_bots") or {}
            mine  = {k:v for k,v in all_b.items() if v.get("owner") == uid}
            enabled_count  = sum(1 for v in mine.values() if v.get("notif_enabled", True))
            disabled_count = len(mine) - enabled_count
            await update.message.reply_text(
                f"{R}🔔 <b>بەشی ئاگادارکردنەوە</b>\n"
                f"{R}━━━━━━━━━━━━━━━━━━━\n"
                f"{R}🤖 بۆتەکانت: <b>{len(mine)}</b>\n"
                f"{R}✅ ئاگادارکردنەوەی چالاک: <b>{enabled_count}</b>\n"
                f"{R}❌ ئاگادارکردنەوەی کوژاو: <b>{disabled_count}</b>\n"
                f"{R}━━━━━━━━━━━━━━━━━━━\n"
                f"{R}👇 هەڵبژێرە:",
                parse_mode="HTML", reply_markup=KB_NOTIF_MAIN()
            )
            return
        if txt == "🔔 چالاككردنی ئاگادارکردنەوەی /start":
            R = "\u200f"
            all_b = await db_get("managed_bots") or {}
            mine  = {k:v for k,v in all_b.items() if v.get("owner") == uid}
            for bid_k, binfo in mine.items():
                binfo["notif_enabled"] = True
                await db_put(f"managed_bots/{bid_k}", binfo)
            await update.message.reply_text(
                f"{R}🔔 <b>ئاگادارکردنەوەی /start چالاک کرا</b>\n\n"
                f"{R}📌 ئێستا کاتێک بەکارهێنەرێک یەکەم جار /start کرد\n"
                f"{R}   نامەی ئاگادارکردنەوە دەگرێیت 🔔",
                parse_mode="HTML", reply_markup=KB_NOTIF_MAIN()
            )
            return
        if txt == "🔕 کوژاندنی ئاگادارکردنەوەی /start":
            R = "\u200f"
            all_b = await db_get("managed_bots") or {}
            mine  = {k:v for k,v in all_b.items() if v.get("owner") == uid}
            for bid_k, binfo in mine.items():
                binfo["notif_enabled"] = False
                await db_put(f"managed_bots/{bid_k}", binfo)
            await update.message.reply_text(
                f"{R}🔕 <b>ئاگادارکردنەوەی /start کوژێنرایەوە</b>\n\n"
                f"{R}📌 ئێستا کاتێک بەکارهێنەرێک /start کرد\n"
                f"{R}   ئاگادار ناکرێیتەوە",
                parse_mode="HTML", reply_markup=KB_NOTIF_MAIN()
            )
            return
        if txt == "📢 ئاگادارکردنەوەی بۆ بەکارهێنەرانی بۆتی سەرەکی":
            await db_put(f"users/{uid}/state", "notif_master")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            R = "\u200f"
            await update.message.reply_text(
                f"{R}📢 <b>ئاگادارکردنەوەی بۆتی سەرەکی</b>\n\n"
                f"{R}📨 ئەم نامەیە دەچێت بۆ هەموو بەکارهێنەرانی بۆتی دروستکەری بۆت\n\n"
                f"{R}⬇️ نامەکەت بنووسە:",
                parse_mode="HTML", reply_markup=kb
            )
            return
        if txt == "🔔 ئاگادارکردنەوەی بەکارهێنەران":
            await db_put(f"users/{uid}/state", "notif_all")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            R = "\u200f"
            await update.message.reply_text(
                f"{R}🔔 <b>ئاگادارکردنەوەی بەکارهێنەران</b>\n\n"
                f"{R}📨 ئەم نامەیە دەچێت بۆ هەموو بەکارهێنەرانی بۆتەکەت\n\n"
                f"{R}⬇️ نامەکەت بنووسە:",
                parse_mode="HTML", reply_markup=kb
            )
            return
        if txt == "📡 ناردنی نامە بۆ هەموو بۆتەکان":
            await db_put(f"users/{uid}/state", "notif_all_bots")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            R = "\u200f"
            # ژمارەی هەموو بەکارهێنەران لە هەموو بۆتەکان
            all_b   = await db_get("managed_bots") or {}
            bot_uids: set = set()
            for bid_k in all_b:
                bu = await db_get(f"bot_users/{bid_k}") or {}
                bot_uids.update(bu.keys())
            await update.message.reply_text(
                f"{R}📡 <b>ناردنی نامە بۆ هەموو بۆتەکان</b>\n\n"
                f"{R}📊 کۆی بەکارهێنەران لە هەموو بۆتەکاندا: <b>{len(bot_uids)}</b> کەس\n"
                f"{R}🤖 ژمارەی بۆتەکان: <b>{len(all_b)}</b>\n\n"
                f"{R}⬇️ نامەکەت بنووسە:",
                parse_mode="HTML", reply_markup=kb
            )
            return

        # ════ بەشی سیستەم ═════════════════════════════════════════════════
        if txt == "⚙️ بەشی سیستەم":
            await update.message.reply_text("⚙️ <b>بەشی سیستەم</b>\n\nهەڵبژاردنێک بکە:", parse_mode="HTML", reply_markup=KB_SYS())
            return
        if txt == "⚙️ زانیاری سیستەم":
            await owner_sys_info(update)
            return
        if txt == "🔄 نوێکردنەوەی هەموو وەبهووک":
            await owner_refresh_all_webhooks(update)
            return
        if txt == "🗑 پاككردنی داتابەیس":
            await db_put(f"users/{uid}/state", "confirm_clear_db")
            kb = IKM([[IKB("✅ بەڵێ، پاک بکەرەوە", "own_sys_clear_yes")], [IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("⚠️ <b>دڵنیایت؟</b> هەموو داتاکان دەسڕیتەوە!", parse_mode="HTML", reply_markup=kb)
            return
        if txt == "💾 پشتگیری داتابەیس":
            await owner_backup_db(update)
            return
        if txt == "📝 گۆڕینی بۆتی سەرەکی":
            await db_put(f"users/{uid}/state", "change_master_token")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🔑 تۆکێنی نوێی بۆتی سەرەکی بنووسە:", reply_markup=kb)
            return
        if txt == "🌐 گۆڕینی PROJECT URL":
            await db_put(f"users/{uid}/state", "change_project_url")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            cur = await db_get("system/project_url") or PROJECT_URL or "نییە"
            await update.message.reply_text(f"🌐 URL ی ئێستا: <code>{cur}</code>\n\nURL ی نوێ بنووسە:", parse_mode="HTML", reply_markup=kb)
            return
        if txt == "📋 لۆگەکان":
            await owner_show_logs(update)
            return
        if txt == "🔃 ڕیستارتی سیستەم":
            await db_put(f"users/{uid}/state", "confirm_restart")
            kb = IKM([[IKB("✅ بەڵێ، ڕیستارت بکە", "own_sys_restart_yes")], [IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("⚠️ دڵنیایت لە ڕیستارتکردنی سیستەم؟", reply_markup=kb)
            return
        if txt == "📢 گۆڕینی کانالی بەڕێوەبەر":
            await db_put(f"users/{uid}/state", "change_dev_channel")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("📢 یوزەرنەیمی کانالی بەڕێوەبەری نوێ بنووسە (بەبێ @):", reply_markup=kb)
            return
        if txt == "🖼 گۆڕینی وێنەی بەخێرهاتن":
            await db_put(f"users/{uid}/state", "change_photo_url")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text("🖼 لینکی وێنەی نوێ بنووسە:", reply_markup=kb)
            return

        # ════ جۆینی ناچاری بۆ بۆتی بەکارهێنەران ════════════════════════════
        if txt == "🌐 جۆینی ناچاری بۆتەکان":
            R = "\u200f"
            all_b = await db_get("managed_bots") or {}
            chs   = await db_get("system/child_fj_channels") or {}
            fj_on = await db_get("system/child_fj_enabled") or False
            await send_and_track(update, uid,
                f"{R}🌐 <b>جۆینی ناچاری بۆ بۆتی بەکارهێنەران</b>\n"
                f"{R}━━━━━━━━━━━━━━━━━━━\n"
                f"{R}🤖 کۆی بۆتەکان: <b>{len(all_b)}</b>\n"
                f"{R}📢 کانالەکان: <b>{len(chs)}</b>\n"
                f"{R}{'✅ چالاک' if fj_on else '❌ لەکارخراو'}\n"
                f"{R}━━━━━━━━━━━━━━━━━━━\n"
                f"{R}👇 هەڵبژێرە:",
                parse_mode="HTML", reply_markup=KB_CHILD_FJ()
            )
            return
        if txt == "➕ زیادکردنی کانال بۆ هەموو بۆتەکان":
            await db_put(f"users/{uid}/state", "child_fj_add_ch")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text(
                "📢 یوزەرنەیمی کانالەکە بنووسە (بەبێ @):\nنموونە: <code>my_channel</code>",
                parse_mode="HTML", reply_markup=kb
            )
            return
        if txt == "➖ لابردنی کانال لە هەموو بۆتەکان":
            await db_put(f"users/{uid}/state", "child_fj_del_ch")
            chs = await db_get("system/child_fj_channels") or {}
            if not chs:
                await update.message.reply_text("📭 هیچ کانالێک زیادنەکراوە.", reply_markup=KB_CHILD_FJ())
                return
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            lines = "\n".join([f"• @{c}" for c in chs.keys()])
            await update.message.reply_text(f"📋 کانالەکان:\n{lines}\n\nیوزەرنەیمی کانالەکە بنووسە (بەبێ @):", reply_markup=kb)
            return
        if txt == "📋 لیستی کانالەکانی جۆینی ناچاری":
            R = "\u200f"
            chs = await db_get("system/child_fj_channels") or {}
            fj_on = await db_get("system/child_fj_enabled") or False
            if not chs:
                await update.message.reply_text(f"{R}📭 هیچ کانالێک زیادنەکراوە.", reply_markup=KB_CHILD_FJ())
                return
            lines = [f"{R}📋 <b>کانالەکانی جۆینی ناچاری:</b> ({'✅ چالاک' if fj_on else '❌ کوژاو'})\n"]
            for c in chs.keys():
                lines.append(f"• @{c}")
            await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=KB_CHILD_FJ())
            return
        if txt == "🔔 چالاككردنی جۆینی ناچاری بۆ هەموو":
            await db_put("system/child_fj_enabled", True)
            R = "\u200f"
            await update.message.reply_text(f"{R}✅ <b>جۆینی ناچاری چالاک کرا بۆ هەموو بۆتەکان</b>", parse_mode="HTML", reply_markup=KB_CHILD_FJ())
            return
        if txt == "🔕 کوژاندنی جۆینی ناچاری بۆ هەموو":
            await db_put("system/child_fj_enabled", False)
            R = "\u200f"
            await update.message.reply_text(f"{R}🔕 <b>جۆینی ناچاری کوژێنرایەوە بۆ هەموو بۆتەکان</b>", parse_mode="HTML", reply_markup=KB_CHILD_FJ())
            return

    # ════════════════════════════════════════════════════════════════════════
    # دۆخەکانی چاوەڕوانی
    # ════════════════════════════════════════════════════════════════════════
    await handle_states(update, uid, txt, state)


# ══════════════════════════════════════════════════════════════════════════════
# ── نیشاندانی Owner Main
# ══════════════════════════════════════════════════════════════════════════════
async def show_owner_main(update: Update, uid: int = None):
    uid = uid or update.effective_user.id
    all_b  = await db_get("managed_bots") or {}
    all_u  = await db_get("users")         or {}
    all_v  = await db_get("vip")           or {}
    all_bl = await db_get("blocked")       or {}
    admins = await db_get("admins")        or {}
    run    = sum(1 for v in all_b.values() if v.get("status") == "running")
    notif_on = await db_get("system/notifications_enabled")
    fj       = await db_get("system/force_join") or False
    R = "\u200f"
    msg = (
        f"{R}‼️ <b>پانێلی سەرەکی</b>\n"
        f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{R}👥 بەکارهێنەران:   <b>{len(all_u)}</b>\n"
        f"{R}🤖 بۆتەکان:        <b>{len(all_b)}</b>  (🟢{run}  🔴{len(all_b)-run})\n"
        f"{R}💎 VIPەکان:        <b>{len(all_v)}</b>\n"
        f"{R}🚫 بلۆکەکان:       <b>{len(all_bl)}</b>\n"
        f"{R}👨‍\u200d💼 ئەدمینەکان:     <b>{len(admins)}</b>\n"
        f"{R}🔔 ئاگادارکردنەوە: <b>{'چالاک ✅' if notif_on else 'لەکارخراو ❌'}</b>\n"
        f"{R}📢 جۆینی ناچاری:   <b>{'چالاک ✅' if fj else 'لەکارخراو ❌'}</b>\n"
        f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{R}📌 بەشێک هەڵبژێرە:"
    )
    await send_and_track(update, uid, msg, parse_mode="HTML", reply_markup=KB_OWNER_MAIN())


# ══════════════════════════════════════════════════════════════════════════════
# ── نیشاندانی لیست / کۆنترۆڵ
# ══════════════════════════════════════════════════════════════════════════════
async def show_bot_list(update: Update, uid: int):
    all_b = await db_get("managed_bots") or {}
    mine  = {k: v for k, v in all_b.items() if v.get("owner") == uid}
    if not mine:
        await send_and_track(update, uid,
            "📭 <b>هیچ بۆتێکت دروست نەکردووە!</b>\n\nکلیک لە '➕ دروستکردنی بۆتی نوێ' بکە.",
            parse_mode="HTML", reply_markup=kb_main(uid),
        )
        return
    rows = []
    for bid_k, info in mine.items():
        st   = "🟢" if info.get("status") == "running" else "🔴"
        btype = info.get("type","reaction")
        ticon = "🍓" if btype == "reaction" else ("🌤️" if btype == "weather" else "🪪")
        rows.append([IKB(f"{st} {ticon} @{info.get('bot_username','Bot')}", f"sel_bot_{bid_k}")])
    rows.append([IKB("🔙 گەڕانەوە بۆ سەرەتا", "back_home")])
    await send_and_track(update, uid,
        f"‏📂 <b>بۆتەکانت ({len(mine)}):</b>\n‏🟢 کاردەکات  |  🔴 ڕاگیراوە\n‏🍓 ڕیاکشن  |  🪪 زانیاری  |  🌤️ کەش و هەوا",
        parse_mode="HTML",
        reply_markup=IKM(rows),
    )


async def show_bot_control(update: Update, uid: int, bid: str, info: dict):
    R = "\u200f"  # RTL mark
    st_icon  = "🟢" if info.get("status") == "running" else "🔴"
    st_txt   = f"{R}چالاک ✅" if info.get("status") == "running" else f"{R}ڕاگیراوە ❌"
    name     = html.escape(info.get("bot_name", "ناسناو"))
    un       = info.get("bot_username", "ناسناو")
    bu       = await db_get(f"bot_users/{bid}") or {}
    wlcm     = info.get("welcome_msg", "")
    btype    = info.get("type", "reaction")
    notif_on = info.get("notif_enabled", True)
    type_lbl = "🍓 بۆتی ڕیاکشن" if btype == "reaction" else ("🌤️ بۆتی کەش و هەوا" if btype == "weather" else "🪪 بۆتی زانیاری")

    msg = (
        f"{R}⚙️ <b>پانێلی کۆنترۆڵ</b>\n"
        f"{R}━━━━━━━━━━━━━━━━━━━\n"
        f"{R}🤖 <b>ناو:</b> {name}\n"
        f"{R}🔗 <b>یوزەر:</b> @{un}\n"
        f"{R}🆔 <b>ID:</b> <code>{bid}</code>\n"
        f"{R}━━━━━━━━━━━━━━━━━━━\n"
        f"{R}{st_icon} <b>دۆخ:</b> {st_txt}\n"
        f"{R}🎯 <b>جۆر:</b> {type_lbl}\n"
        f"{R}👥 <b>بەکارهێنەران:</b> <b>{len(bu)}</b> کەس\n"
        f"{R}✉️ <b>بەخێرهاتن:</b> {'✅ دانراوە' if wlcm else '❌ بەتاڵ'}\n"
        f"{R}🔔 <b>ئاگادارکردنەوە:</b> {'✅ چالاک' if notif_on else '❌ کوێژاو'}\n"
        f"{R}━━━━━━━━━━━━━━━━━━━"
    )
    await send_and_track(update, uid, msg, parse_mode="HTML", reply_markup=kb_control(uid))


async def show_stats(update: Update, uid: int):
    all_b = await db_get("managed_bots") or {}
    all_u = await db_get("users")         or {}
    mine  = {k: v for k, v in all_b.items() if v.get("owner") == uid}
    run_m = sum(1 for v in mine.values() if v.get("status") == "running")
    R = "\u200f"
    if uid == OWNER_ID:
        run_a = sum(1 for v in all_b.values() if v.get("status") == "running")
        all_v = await db_get("vip") or {}
        admins = await db_get("admins") or {}
        txt   = (
            f"{R}📊 <b>ئامارەکانی سیستەم</b>\n"
            f"{R}━━━━━━━━━━━━━━━━━━━\n"
            f"{R}👥 هەموو بەکارهێنەران: <b>{len(all_u)}</b>\n"
            f"{R}🤖 هەموو بۆتەکان:      <b>{len(all_b)}</b>\n"
            f"{R}🟢 چالاک: <b>{run_a}</b>  🔴 ڕاگیراو: <b>{len(all_b)-run_a}</b>\n"
            f"{R}💎 VIPەکان: <b>{len(all_v)}</b>\n"
            f"{R}👨\u200d💼 ئەدمینەکان: <b>{len(admins)}</b>\n"
            f"{R}━━━━━━━━━━━━━━━━━━━\n"
            f"{R}📁 بۆتەکانی خۆت: <b>{len(mine)}</b>  (🟢{run_m})"
        )
    else:
        bu_count = 0
        for k, v in mine.items():
            bu = await db_get(f"bot_users/{k}") or {}
            bu_count += len(bu)
        vip_badge = "💎 VIP" if await is_vip(uid) else "👤 ئاسایی"
        txt = (
            f"{R}📊 <b>ئامارەکانت</b>\n"
            f"{R}━━━━━━━━━━━━━━━━━━━\n"
            f"{R}🎖 دۆخ: <b>{vip_badge}</b>\n"
            f"{R}🤖 بۆتی دروستکردوو: <b>{len(mine)}</b>\n"
            f"{R}🟢 چالاک: <b>{run_m}</b>  🔴 ڕاگیراو: <b>{len(mine)-run_m}</b>\n"
            f"{R}👥 کۆی بەکارهێنەرانی بۆتەکانت: <b>{bu_count}</b>"
        )
    await send_and_track(update, uid, txt, parse_mode="HTML", reply_markup=kb_main(uid))


# ══════════════════════════════════════════════════════════════════════════════
# ── کۆنترۆڵی بۆت
# ══════════════════════════════════════════════════════════════════════════════
async def handle_control(update: Update, uid: int, txt: str):
    bid = await db_get(f"users/{uid}/selected_bot")
    if not bid:
        await update.message.reply_text("⚠️ تکایە سەرەتا بۆتێک هەڵبژێرە.", reply_markup=kb_main(uid))
        return
    info = await db_get(f"managed_bots/{bid}")
    if not info:
        await db_del(f"users/{uid}/selected_bot")
        await update.message.reply_text("❌ بۆتەکە سڕاوەتەوە.", reply_markup=kb_main(uid))
        return
    un    = info.get("bot_username","Bot")
    token = info.get("token","")

    if txt == "▶️ دەستپێکردن":
        info["status"] = "running"
        await db_put(f"managed_bots/{bid}", info)
        await update.message.reply_text(f"✅ بۆتی @{un} دەستی پێکرد 🟢", reply_markup=kb_control(uid))

    elif txt == "⏸ وەستاندن":
        info["status"] = "stopped"
        await db_put(f"managed_bots/{bid}", info)
        await update.message.reply_text(f"🛑 بۆتی @{un} وەستاندرا 🔴", reply_markup=kb_control(uid))

    elif txt == "🔄 نوێکردنەوە":
        info["status"] = "running"
        await db_put(f"managed_bots/{bid}", info)
        await update.message.reply_text(f"🔄 بۆتی @{un} نوێکرایەوە ✅", reply_markup=kb_control(uid))

    elif txt == "📋 زانیاری بۆت":
        await show_bot_control(update, uid, bid, info)

    elif txt == "✏️ گۆڕینی بەخێرهاتن":
        await db_put(f"users/{uid}/state", f"edit_welcome:{bid}")
        cur = info.get("welcome_msg","")
        kb  = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
        await update.message.reply_text(
            "✏️ <b>گۆڕینی نامەی بەخێرهاتن</b>\n\n"
            f"📝 نامەی ئێستا:\n<code>{html.escape(cur) if cur else '(بەتاڵ)'}</code>\n\n"
            "نامەی نوێت بنووسە:\n💡 <code>{name}</code> بەکاربهێنە بۆ ناوی بەکارهێنەر",
            parse_mode="HTML", reply_markup=kb,
        )

    elif txt == "📨 پەیام بۆ بەکارهێنەران":
        bu = await db_get(f"bot_users/{bid}") or {}
        if not bu:
            await update.message.reply_text("📭 هیچ بەکارهێنەرێک بۆتەکەت بەکار نەهێناوە.", reply_markup=kb_control(uid))
            return
        await db_put(f"users/{uid}/state", f"bot_bc:{bid}")
        kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
        await update.message.reply_text(
            f"📨 <b>بڵاوکردنەوە بۆ بەکارهێنەرانی @{un}</b>\n\n"
            f"👥 ژمارە: <b>{len(bu)}</b>\n\nپەیامەکەت بنووسە:",
            parse_mode="HTML", reply_markup=kb,
        )

    elif txt == "🔗 نوێکردنەوەی وەبهووک" and uid == OWNER_ID:
        if token:
            safe = (PROJECT_URL or "").rstrip('/')
            r    = await send_tg(token,"setWebhook",{"url":f"{safe}/api/bot/{token}","allowed_updates":["message","channel_post","callback_query"]})
            resp = "✅ وەبهووک نوێکرایەوە!" if r.get("ok") else f"❌ هەڵە: {r.get('description','')}"
            await update.message.reply_text(resp, reply_markup=kb_control(uid))
        else:
            await update.message.reply_text("❌ تۆکێن نەدۆزرایەوە.", reply_markup=kb_control(uid))

    elif txt == "🔑 گۆڕینی تۆکێن" and uid == OWNER_ID:
        await db_put(f"users/{uid}/state", f"change_token:{bid}")
        kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
        await update.message.reply_text("🔑 تۆکێنی نوێ بنووسە:", reply_markup=kb)

    elif txt == "🗑 سڕینەوەی بۆت":
        await db_put(f"users/{uid}/state", f"confirm_del:{bid}")
        kb = IKM([
            [IKB(f"✅ بەڵێ، @{un} بسڕەوە", f"confirm_del_yes_{bid}")],
            [IKB("❌ نەخێر، دەرچوون", "cancel_state")],
        ])
        await update.message.reply_text(
            f"⚠️ <b>دڵنیایت؟</b>\n\nبۆتی @{un} بە تەواوی دەسڕیتەوە!",
            parse_mode="HTML", reply_markup=kb,
        )


# ══════════════════════════════════════════════════════════════════════════════
# ── دۆخەکانی چاوەڕوانی
# ══════════════════════════════════════════════════════════════════════════════
async def handle_states(update: Update, uid: int, txt: str, state: str):

    if txt == "❌ هەڵوەشاندنەوە":
        await db_del(f"users/{uid}/state")
        await update.message.reply_text("↩️ هەڵوەشاندرایەوە.", reply_markup=kb_main(uid))
        return

    # ── هەڵبژاردنی جۆری بۆت ──────────────────────────────────────────────
    if state == "choose_bot_type":
        bid = await db_get(f"users/{uid}/pending_bot_id")
        if not bid:
            await db_del(f"users/{uid}/state")
            await update.message.reply_text("❌ هەڵەیەک ڕوویدا.", reply_markup=kb_main(uid))
            return
        R = "\u200f"
        if txt == "🍓 بۆتی ڕیاکشن":
            binfo = await db_get(f"managed_bots/{bid}") or {}
            binfo["type"] = "reaction"
            await db_put(f"managed_bots/{bid}", binfo)
            await db_del(f"users/{uid}/state")
            await db_del(f"users/{uid}/pending_bot_id")
            await db_put(f"users/{uid}/selected_bot", bid)
            await update.message.reply_text(
                f"{R}🍓 <b>بۆتی ڕیاکشن هەڵبژێردرا</b>\n\n"
                f"{R}📌 پێنج هەنگاوی داهاتوو:\n"
                f"{R}١. بۆتەکەت زیاد بکە بۆ گروپ/کانالەکەت\n"
                f"{R}٢. ئادمینی تەواوی پێ بدە\n"
                f"{R}٣. ئینجا بۆ هەموو نامەیەک ئیموجی دەنێرێت 🍓\n"
                f"{R}🔔 هەربەکارهێنەرێک /start کرد ئاگادار دەکرێیتەوە",
                parse_mode="HTML", reply_markup=kb_control(uid)
            )
        elif txt == "🪪 بۆتی زانیاری":
            binfo = await db_get(f"managed_bots/{bid}") or {}
            binfo["type"] = "info"
            await db_put(f"managed_bots/{bid}", binfo)
            await db_del(f"users/{uid}/state")
            await db_del(f"users/{uid}/pending_bot_id")
            await db_put(f"users/{uid}/selected_bot", bid)
            await update.message.reply_text(
                f"{R}🪪 <b>بۆتی زانیاری هەڵبژێردرا</b>\n\n"
                f"{R}📌 فەرمانەکان:\n"
                f"{R}▪️ /id — زانیاری تەواوی بەکارهێنەر\n"
                f"{R}▪️ /info — وەک /id\n\n"
                f"{R}📌 پێنج هەنگاوی داهاتوو:\n"
                f"{R}١. بۆتەکەت زیاد بکە بۆ گروپ/کانالەکەت\n"
                f"{R}٢. ئادمینی تەواوی پێ بدە\n"
                f"{R}٣. /id بنووسە تا زانیاریت ببینیت 🪪\n"
                f"{R}🔔 هەربەکارهێنەرێک /start کرد ئاگادار دەکرێیتەوە",
                parse_mode="HTML", reply_markup=kb_control(uid)
            )
        elif txt == "🌤️ بۆتی کەش و هەوا":
            binfo = await db_get(f"managed_bots/{bid}") or {}
            binfo["type"] = "weather"
            await db_put(f"managed_bots/{bid}", binfo)
            await db_del(f"users/{uid}/state")
            await db_del(f"users/{uid}/pending_bot_id")
            await db_put(f"users/{uid}/selected_bot", bid)
            await update.message.reply_text(
                f"{R}🌤️ <b>بۆتی کەش و هەوا هەڵبژێردرا</b>\n\n"
                f"{R}📌 ئەم بۆتە:\n"
                f"{R}▪️ کەش و هەوای ٥٠+ شاری کوردستان\n"
                f"{R}▪️ پێشبینی ٣ و ٧ ڕۆژ\n"
                f"{R}▪️ زانیاری ساعاتانە\n\n"
                f"{R}📌 هەنگاوەکان:\n"
                f"{R}١. /start بنووسە لە بۆتەکەت\n"
                f"{R}٢. ناوچە و شار هەڵبژێرە\n"
                f"{R}🔔 هەربەکارهێنەرێک /start کرد ئاگادار دەکرێیتەوە",
                parse_mode="HTML", reply_markup=kb_control(uid)
            )
        return

    # ── چاوەڕوانی تۆکێن ──────────────────────────────────────────────────
    if state == "await_token":
        if re.match(r"^\d{8,10}:[A-Za-z0-9_-]{35}$", txt):
            await activate_token(update, uid, txt)
        else:
            await update.message.reply_text("⚠️ تۆکێنەکە دروست نییە.\nنموونە: <code>123456789:ABCxyz...</code>", parse_mode="HTML")
        return

    # ── دڵنیاکردنەوەی سڕینەوەی بۆت ──────────────────────────────────────
    if state.startswith("confirm_del:"):
        bid = state.split(":",1)[1]
        if txt.startswith("✅ بەڵێ،"):
            await do_delete_bot(update, uid, bid)
        else:
            await db_del(f"users/{uid}/state")
            await update.message.reply_text("↩️ گەڕایتەوە.", reply_markup=kb_control(uid))
        return

    # ── گۆڕینی بەخێرهاتن ──────────────────────────────────────────────────
    if state.startswith("edit_welcome:"):
        bid  = state.split(":",1)[1]
        info = await db_get(f"managed_bots/{bid}")
        if not info:
            await db_del(f"users/{uid}/state")
            await update.message.reply_text("❌ بۆتەکە نەدۆزرایەوە.", reply_markup=kb_main(uid))
            return
        info["welcome_msg"] = txt
        await db_put(f"managed_bots/{bid}", info)
        await db_del(f"users/{uid}/state")
        await update.message.reply_text("✅ <b>نامەی بەخێرهاتن نوێکرا!</b>", parse_mode="HTML", reply_markup=kb_control(uid))
        return

    # ── بڵاوکردنەوەی بۆت ─────────────────────────────────────────────────
    if state.startswith("bot_bc:"):
        bid   = state.split(":",1)[1]
        info  = await db_get(f"managed_bots/{bid}") or {}
        token = info.get("token","")
        bu    = await db_get(f"bot_users/{bid}") or {}
        # خێراکردن بەپێی VIP
        vip_user = await is_vip(uid)
        delay = 0.02 if vip_user else 0.05
        sm    = await update.message.reply_text(f"⏳ ناردن بۆ {len(bu)} بەکارهێنەر...")
        sent=fail=0
        for cid in bu.keys():
            try:
                r = await send_tg(token,"sendMessage",{"chat_id":int(cid),"text":txt,"parse_mode":"HTML"})
                if r.get("ok"): sent+=1
                else: fail+=1
            except: fail+=1
            await asyncio.sleep(delay)
        await db_del(f"users/{uid}/state")
        await sm.edit_text(f"✅ <b>تەواو!</b> 📤{sent}  ❌{fail}", parse_mode="HTML")
        await update.message.reply_text(".", reply_markup=kb_control(uid))
        return

    # ── گۆڕینی تۆکێن ─────────────────────────────────────────────────────
    if state.startswith("change_token:") and uid == OWNER_ID:
        bid = state.split(":",1)[1]
        if re.match(r"^\d{8,10}:[A-Za-z0-9_-]{35}$", txt):
            res = await send_tg(txt,"getMe",{})
            if not res.get("ok"):
                await update.message.reply_text("❌ تۆکێنەکە هەڵەیە.", reply_markup=kb_control(uid))
                await db_del(f"users/{uid}/state")
                return
            info = await db_get(f"managed_bots/{bid}") or {}
            info["token"]        = txt
            info["bot_username"] = res["result"]["username"]
            info["bot_name"]     = res["result"]["first_name"]
            await db_put(f"managed_bots/{bid}", info)
            safe = (PROJECT_URL or "").rstrip('/')
            await send_tg(txt,"setWebhook",{"url":f"{safe}/api/bot/{txt}","allowed_updates":["message","channel_post","callback_query"]})
            await db_del(f"users/{uid}/state")
            await update.message.reply_text("✅ تۆکێن گۆڕدرا!", reply_markup=kb_control(uid))
        else:
            await update.message.reply_text("⚠️ تۆکێنەکە دروست نییە.")
        return

    # ══════════════════════════════════════════════════════════════════════
    # دۆخەکانی Owner
    # ══════════════════════════════════════════════════════════════════════
    if uid != OWNER_ID and not await is_admin(uid):
        if re.match(r"^\d{8,10}:[A-Za-z0-9_-]{35}$", txt):
            await update.message.reply_text("⚠️ تکایە لەسەرەتاوە '➕ دروستکردنی بۆتی نوێ' بکلیک بکە.", reply_markup=kb_main(uid))
        else:
            await update.message.reply_text("تکایە لە کیبۆردی خوارەوە هەڵبژێرە 👇", reply_markup=kb_main(uid))
        return

    # ── بڵاوکردنەوەی گشتی ────────────────────────────────────────────────
    if state in ("bc_all","bc_vip","bc_nonvip","notif_all","notif_vip","notif_master","notif_all_bots"):
        R = "\u200f"
        all_u   = await db_get("users") or {}
        all_v   = await db_get("vip")   or {}
        vip_ids = set(all_v.keys())
        is_notif = state.startswith("notif_")

        if state == "notif_all_bots":
            # بۆ هەموو بەکارهێنەرانی هەموو بۆتەکان
            all_b = await db_get("managed_bots") or {}
            seen_ids: set = set()
            targets = []
            for bid_k in all_b:
                bu = await db_get(f"bot_users/{bid_k}") or {}
                for u_id in bu:
                    if u_id not in seen_ids:
                        seen_ids.add(u_id)
                        targets.append(u_id)
        elif state in ("bc_all", "notif_all"):
            targets = list(all_u.keys())
        elif state in ("bc_vip", "notif_vip"):
            targets = [i for i in all_u if i in vip_ids]
        elif state == "notif_master":
            targets = list(all_u.keys())
        else:
            targets = [i for i in all_u if i not in vip_ids]

        prefix = f"{R}🔔 <b>ئاگادارکردنەوە:</b>\n\n" if is_notif else ""
        sm   = await update.message.reply_text(f"⏳ ناردن بۆ {len(targets)} بەکارهێنەر...")
        sent=fail=0
        for u_id in targets:
            try:
                r = await send_tg(MASTER_TOKEN,"sendMessage",{"chat_id":int(u_id),"text":prefix+txt,"parse_mode":"HTML"})
                if r.get("ok"): sent+=1
                else: fail+=1
            except: fail+=1
            await asyncio.sleep(0.05)
        await db_del(f"users/{uid}/state")
        hist_key = "system/notif_history" if is_notif else "system/bc_history"
        hist = await db_get(hist_key) or []
        if isinstance(hist, dict): hist = []
        hist.insert(0, {"time": now_str(), "sent": sent, "fail": fail, "type": state})
        await db_put(hist_key, hist[:20])
        await sm.edit_text(f"✅ <b>تەواو!</b>\n{R}📤 نێردرا: <b>{sent}</b>\n{R}❌ شکستهێنا: <b>{fail}</b>", parse_mode="HTML")
        reply_kb = KB_NOTIF if is_notif else KB_MSG
        await update.message.reply_text(".", reply_markup=reply_kb)
        return

    # ── ناردنی پەیام بۆ هەموو بەکارهێنەرانی هەموو بۆتەکان ──────────────
    if state == "bc_all_child_bots":
        R = "\u200f"
        all_b = await db_get("managed_bots") or {}
        vip_user = await is_vip(uid)
        delay = 0.02 if vip_user else 0.05
        sm = await update.message.reply_text(f"{R}⏳ خەریکی ناردنم، تکایە چاوەڕێ بە...")
        total_sent = total_fail = total_bots = 0
        seen_chats: set = set()
        for bid_k, binfo in all_b.items():
            token_k = binfo.get("token","")
            if not token_k: continue
            bu = await db_get(f"bot_users/{bid_k}") or {}
            if not bu: continue
            total_bots += 1
            for u_id, udata in bu.items():
                # chat_id پاشەکەوتکراوە لە bot_users، بەکاربهێنە
                if isinstance(udata, dict):
                    cid = udata.get("chat_id", int(u_id))
                else:
                    cid = int(u_id)
                cid_key = f"{bid_k}:{cid}"
                if cid_key in seen_chats:
                    continue
                seen_chats.add(cid_key)
                try:
                    r = await send_tg(token_k, "sendMessage", {"chat_id": int(cid), "text": txt, "parse_mode": "HTML"})
                    if r.get("ok"): total_sent += 1
                    else: total_fail += 1
                except: total_fail += 1
                await asyncio.sleep(delay)
        await db_del(f"users/{uid}/state")
        await sm.edit_text(
            f"{R}✅ <b>تەواو!</b>\n"
            f"{R}━━━━━━━━━━━━━━━━━━━\n"
            f"{R}🤖 بۆتەکان: <b>{total_bots}</b>\n"
            f"{R}📤 نێردرا: <b>{total_sent}</b>\n"
            f"{R}❌ شکستهێنا: <b>{total_fail}</b>",
            parse_mode="HTML"
        )
        await update.message.reply_text(".", reply_markup=KB_MSG())
        return

    # ── پەیام بۆ بەکارهێنەرێک ────────────────────────────────────────────
    if state == "msg_one_id":
        try:
            target = int(txt.strip())
            await db_put(f"users/{uid}/state", f"msg_one_text:{target}")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text(f"✅ ID: <code>{target}</code>\n\nئێستا پەیامەکەت بنووسە:", parse_mode="HTML", reply_markup=kb)
        except:
            await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    if state.startswith("msg_one_text:"):
        target = int(state.split(":",1)[1])
        r = await send_tg(MASTER_TOKEN,"sendMessage",{"chat_id":target,"text":txt,"parse_mode":"HTML"})
        await db_del(f"users/{uid}/state")
        if r.get("ok"):
            await update.message.reply_text(f"✅ پەیام بۆ <code>{target}</code> نێردرا!", parse_mode="HTML", reply_markup=KB_MSG())
        else:
            await update.message.reply_text(f"❌ هەڵە: {r.get('description','')}", reply_markup=KB_MSG())
        return

    # ── پەیامی سیستەم ────────────────────────────────────────────────────
    if state == "set_sys_msg":
        await db_put("system/notice", txt)
        await db_del(f"users/{uid}/state")
        await update.message.reply_text("✅ پەیامی سیستەم دانرا.", reply_markup=KB_MSG())
        return

    # ── VIP ───────────────────────────────────────────────────────────────
    if state == "add_vip":
        try:
            target = int(txt.strip())
            await db_put(f"vip/{target}", {"expires":"lifetime","added_by":uid,"date":now_str()})
            await db_del(f"users/{uid}/state")
            await update.message.reply_text(f"💎 بەکارهێنەری <code>{target}</code> بوو بە VIP هەمیشەیی!", parse_mode="HTML", reply_markup=KB_VIP())
        except:
            await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    if state == "add_vip_life":
        try:
            target = int(txt.strip())
            await db_put(f"vip/{target}", {"expires":"lifetime","added_by":uid,"date":now_str()})
            await db_del(f"users/{uid}/state")
            await update.message.reply_text(f"💎 <code>{target}</code> بوو بە VIP هەمیشەیی!", parse_mode="HTML", reply_markup=KB_VIP())
        except:
            await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    if state == "add_vip_date":
        parts = txt.strip().split()
        if len(parts) == 2:
            try:
                target = int(parts[0])
                datetime.strptime(parts[1], "%Y-%m-%d")
                await db_put(f"vip/{target}", {"expires":parts[1],"added_by":uid,"date":now_str()})
                await db_del(f"users/{uid}/state")
                await update.message.reply_text(f"💎 <code>{target}</code> بوو بە VIP تا <b>{parts[1]}</b>!", parse_mode="HTML", reply_markup=KB_VIP())
            except:
                await update.message.reply_text("⚠️ فۆرمات هەڵەیە. نموونە: <code>123456789 2025-12-31</code>", parse_mode="HTML")
        else:
            await update.message.reply_text("⚠️ فۆرمات هەڵەیە. نموونە: <code>123456789 2025-12-31</code>", parse_mode="HTML")
        return

    if state == "del_vip":
        try:
            target = int(txt.strip())
            await db_del(f"vip/{target}")
            await db_del(f"users/{uid}/state")
            await update.message.reply_text(f"✅ VIPی <code>{target}</code> لابرا.", parse_mode="HTML", reply_markup=KB_VIP())
        except:
            await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    if state == "check_vip":
        try:
            target  = int(txt.strip())
            vd      = await db_get(f"vip/{target}")
            await db_del(f"users/{uid}/state")
            if vd:
                exp = vd.get("expires","نییە")
                await update.message.reply_text(f"💎 بەکارهێنەری <code>{target}</code> VIPە.\n⏰ بەسەرچوون: <b>{exp}</b>", parse_mode="HTML", reply_markup=KB_VIP())
            else:
                await update.message.reply_text(f"❌ بەکارهێنەری <code>{target}</code> VIP نییە.", parse_mode="HTML", reply_markup=KB_VIP())
        except:
            await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    if state == "confirm_del_all_vip":
        if txt == "✅ بەڵێ، هەموو VIP بسڕەوە":
            await db_del("vip")
            await db_del(f"users/{uid}/state")
            await update.message.reply_text("✅ هەموو VIPەکان سڕایەوە.", reply_markup=KB_VIP())
        else:
            await db_del(f"users/{uid}/state")
            await update.message.reply_text("↩️ هەڵوەشاندرایەوە.", reply_markup=KB_VIP())
        return

    # ── ئەمنیەت ───────────────────────────────────────────────────────────
    if state == "block_user":
        try:
            target = int(txt.strip())
            await db_put(f"blocked/{target}", True)
            await db_del(f"users/{uid}/state")
            await update.message.reply_text(f"🚫 بەکارهێنەری <code>{target}</code> بلۆک کرا.", parse_mode="HTML", reply_markup=KB_SEC())
        except:
            await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    if state == "unblock_user":
        try:
            target = int(txt.strip())
            await db_del(f"blocked/{target}")
            await db_del(f"users/{uid}/state")
            await update.message.reply_text(f"✅ بلۆکی <code>{target}</code> لابرا.", parse_mode="HTML", reply_markup=KB_SEC())
        except:
            await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    if state == "warn_user_id":
        try:
            target = int(txt.strip())
            await db_put(f"users/{uid}/state", f"warn_user_msg:{target}")
            kb = IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]])
            await update.message.reply_text(f"⚠️ نامەی ئاگادارکردنەوە بنووسە بۆ <code>{target}</code>:", parse_mode="HTML", reply_markup=kb)
        except:
            await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    if state.startswith("warn_user_msg:"):
        target = int(state.split(":",1)[1])
        warns  = await db_get(f"warnings/{target}") or 0
        new_w  = warns + 1
        await db_put(f"warnings/{target}", new_w)
        r = await send_tg(MASTER_TOKEN,"sendMessage",{"chat_id":target,"text":f"⚠️ <b>ئاگادارکردنەوە #{new_w}</b>\n\n{txt}","parse_mode":"HTML"})
        await db_del(f"users/{uid}/state")
        if r.get("ok"):
            await update.message.reply_text(f"✅ ئاگادارکردنەوە #{new_w} نێردرا.", reply_markup=KB_SEC())
        else:
            await update.message.reply_text(f"❌ هەڵە لە ناردن: {r.get('description','')}", reply_markup=KB_SEC())
        return

    if state == "restrict_feat":
        await db_put(f"system/restricted/{txt.strip()}", True)
        await db_del(f"users/{uid}/state")
        await update.message.reply_text(f"🔒 فیچەری <code>{txt}</code> قەدەغەکرا.", parse_mode="HTML", reply_markup=KB_SEC())
        return

    if state == "del_user":
        try:
            target = int(txt.strip())
            await db_del(f"users/{target}")
            await db_del(f"users/{uid}/state")
            await update.message.reply_text(f"🗑 بەکارهێنەری <code>{target}</code> سڕایەوە.", parse_mode="HTML", reply_markup=KB_USERS())
        except:
            await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    if state == "search_user":
        all_u = await db_get("users") or {}
        results = []
        for u_id, ud in all_u.items():
            if (txt.lower() in ud.get("name","").lower() or
                txt.lower() in ud.get("username","").lower() or
                txt == u_id):
                results.append((u_id, ud))
        await db_del(f"users/{uid}/state")
        if not results:
            await update.message.reply_text("❌ بەکارهێنەرێک نەدۆزرایەوە.", reply_markup=KB_USERS())
            return
        lines = [f"🔍 <b>ئەنجامی گەڕان ({len(results)}):</b>\n"]
        for u_id, ud in results[:10]:
            n  = html.escape(ud.get("name","ناسناو"))
            un = f"@{ud['username']}" if ud.get("username") else "—"
            lines.append(f"• <a href='tg://user?id={u_id}'>{n}</a> {un} <code>{u_id}</code>")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=KB_USERS())
        return

    if state == "user_info_id":
        try:
            target = int(txt.strip())
            ud     = await db_get(f"users/{target}") or {}
            await db_del(f"users/{uid}/state")
            vd     = await db_get(f"vip/{target}")
            bl     = await db_get(f"blocked/{target}")
            warns  = await db_get(f"warnings/{target}") or 0
            adm    = await db_get(f"admins/{target}")
            vip_txt= f"💎 VIP ({vd.get('expires','')})" if vd else "❌ نا-VIP"
            bl_txt = "🚫 بلۆک" if bl else "✅ ئازاد"
            adm_txt = "🛡 ئەدمین" if adm else "👤 ئاسایی"
            msg    = (
                f"👤 <b>زانیاری بەکارهێنەر</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 ID: <code>{target}</code>\n"
                f"📛 ناو: {html.escape(ud.get('name','ناسناو'))}\n"
                f"🔗 یوزەر: @{ud.get('username','—')}\n"
                f"💎 دۆخ: {vip_txt}\n"
                f"🛡 ئەدمین: {adm_txt}\n"
                f"🚫 بلۆک: {bl_txt}\n"
                f"⚠️ ئاگادارکردنەوە: {warns}\n"
                f"🕐 کاتی دوایین چالاکی: {ud.get('last_seen','نییە')}"
            )
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=KB_USERS())
        except:
            await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    if state == "search_bot":
        all_b = await db_get("managed_bots") or {}
        results = [(k,v) for k,v in all_b.items()
                   if txt.lower() in v.get("bot_username","").lower() or txt == k]
        await db_del(f"users/{uid}/state")
        if not results:
            await update.message.reply_text("❌ بۆتێک نەدۆزرایەوە.", reply_markup=KB_BOTS())
            return
        lines = [f"🔍 <b>ئەنجامی گەڕان ({len(results)}):</b>\n"]
        for bid, bd in results[:10]:
            st  = "🟢" if bd.get("status") == "running" else "🔴"
            own = bd.get("owner","؟")
            lines.append(f"{st} @{bd.get('bot_username','—')}  خاوەن: <code>{own}</code>  ID: <code>{bid}</code>")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=KB_BOTS())
        return

    if state == "owner_del_bot":
        info = await db_get(f"managed_bots/{txt.strip()}")
        await db_del(f"users/{uid}/state")
        if not info:
            await update.message.reply_text("❌ بۆتێک بەم ID ەیە نەدۆزرایەوە.", reply_markup=KB_BOTS())
        else:
            await do_delete_bot(update, uid, txt.strip(), back_kb=KB_BOTS)
        return

    # ── جۆینی ناچاری بۆ بۆتی بەکارهێنەران ──────────────────────────────
    if state == "child_fj_add_ch" and uid == OWNER_ID:
        ch = txt.strip().lstrip("@")
        if not ch:
            await update.message.reply_text("⚠️ یوزەرنەیمی دروست بنووسە.")
            return
        await db_put(f"system/child_fj_channels/{ch}", True)
        await db_del(f"users/{uid}/state")
        R = "\u200f"
        await update.message.reply_text(
            f"{R}✅ کانالی @{ch} زیادکرا بۆ جۆینی ناچاری هەموو بۆتەکان",
            reply_markup=KB_CHILD_FJ()
        )
        return

    if state == "child_fj_del_ch" and uid == OWNER_ID:
        ch = txt.strip().lstrip("@")
        await db_del(f"system/child_fj_channels/{ch}")
        await db_del(f"users/{uid}/state")
        R = "\u200f"
        await update.message.reply_text(
            f"{R}✅ کانالی @{ch} لابرا لە جۆینی ناچاری",
            reply_markup=KB_CHILD_FJ()
        )
        return

    # ── ئەدمین ────────────────────────────────────────────────────────────
    if state == "add_admin" and uid == OWNER_ID:
        try:
            target = int(txt.strip())
            if target == OWNER_ID:
                await update.message.reply_text("⚠️ خاوەنی بۆت پێشەکی ئەدمینی گەورەیە.", reply_markup=KB_ADMINS())
                await db_del(f"users/{uid}/state")
                return
            ud = await db_get(f"users/{target}") or {}
            await db_put(f"admins/{target}", {
                "added_by": uid,
                "date": now_str(),
                "name": ud.get("name","ناسناو"),
            })
            await db_del(f"users/{uid}/state")
            # ئاگادارکردنەوەی ئەدمینی نوێ
            await send_tg(MASTER_TOKEN,"sendMessage",{
                "chat_id": target,
                "text": "‼️ <b>پیرۆزبێت!</b> 🎉\n\nتۆ بوویت بە ئەدمینی بۆتی سیستەم.\n🛡 ئێستا دەستتە بۆ پانێلی ئەدمین.",
                "parse_mode": "HTML"
            })
            await update.message.reply_text(f"✅ بەکارهێنەری <code>{target}</code> بوو بە ئەدمین! 🛡", parse_mode="HTML", reply_markup=KB_ADMINS())
        except:
            await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    if state == "del_admin" and uid == OWNER_ID:
        try:
            target = int(txt.strip())
            adm = await db_get(f"admins/{target}")
            await db_del(f"users/{uid}/state")
            if adm:
                await db_del(f"admins/{target}")
                # ئاگادارکردنەوەی ئەدمینی لابراو
                await send_tg(MASTER_TOKEN,"sendMessage",{
                    "chat_id": target,
                    "text": "⚠️ دەستێوەردانی ئەدمینەکەت لابرا.",
                    "parse_mode": "HTML"
                })
                await update.message.reply_text(f"✅ ئەدمینی <code>{target}</code> لابرا.", parse_mode="HTML", reply_markup=KB_ADMINS())
            else:
                await update.message.reply_text(f"❌ بەکارهێنەری <code>{target}</code> ئەدمین نییە.", parse_mode="HTML", reply_markup=KB_ADMINS())
        except:
            await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    # ── کانال ────────────────────────────────────────────────────────────
    if state == "change_main_channel":
        await db_put("system/channel", txt.strip().lstrip("@"))
        await db_del(f"users/{uid}/state")
        await update.message.reply_text(f"✅ کانالی سەرەکی گۆڕدرا بۆ: @{txt.strip().lstrip('@')}", reply_markup=KB_CHAN())
        return

    if state == "add_req_channel":
        ch = txt.strip().lstrip("@")
        await db_put(f"system/req_channels/{ch}", True)
        await db_del(f"users/{uid}/state")
        await update.message.reply_text(f"✅ کانالی @{ch} زیادکرا.", reply_markup=KB_CHAN())
        return

    if state == "del_req_channel":
        ch = txt.strip().lstrip("@")
        await db_del(f"system/req_channels/{ch}")
        await db_del(f"users/{uid}/state")
        await update.message.reply_text(f"✅ کانالی @{ch} لابرا.", reply_markup=KB_CHAN())
        return

    if state == "check_member":
        try:
            target  = int(txt.strip())
            req_chs = await db_get("system/req_channels") or {}
            if not req_chs:
                await update.message.reply_text("📭 هیچ کانالی داواکراوێک تۆمار نەکراوە.", reply_markup=KB_CHAN())
                await db_del(f"users/{uid}/state")
                return
            lines = [f"🔍 <b>پشکنینی ئەندامی بەکارهێنەری <code>{target}</code></b>\n"]
            for ch in req_chs:
                res = await send_tg(MASTER_TOKEN,"getChatMember",{"chat_id":f"@{ch}","user_id":target})
                status = res.get("result",{}).get("status","unknown")
                ok = status in ("member","administrator","creator")
                lines.append(f"{'✅' if ok else '❌'} @{ch}: {status}")
            await db_del(f"users/{uid}/state")
            await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=KB_CHAN())
        except:
            await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    # ── سیستەم ───────────────────────────────────────────────────────────
    if state == "change_project_url":
        await db_put("system/project_url", txt.strip())
        await db_del(f"users/{uid}/state")
        await update.message.reply_text(f"✅ PROJECT URL گۆڕدرا بۆ:\n<code>{txt.strip()}</code>", parse_mode="HTML", reply_markup=KB_SYS())
        return

    if state == "change_dev_channel":
        await db_put("system/dev_channel", txt.strip().lstrip("@"))
        await db_del(f"users/{uid}/state")
        await update.message.reply_text(f"✅ کانالی بەڕێوەبەر گۆڕدرا بۆ @{txt.strip().lstrip('@')}", reply_markup=KB_SYS())
        return

    if state == "change_photo_url":
        await db_put("system/photo_url", txt.strip())
        await db_del(f"users/{uid}/state")
        await update.message.reply_text("✅ وێنەی بەخێرهاتن گۆڕدرا!", reply_markup=KB_SYS())
        return

    if state == "change_master_token":
        await db_put("system/master_token_note", txt.strip()[:10]+"...")
        await db_del(f"users/{uid}/state")
        await update.message.reply_text(
            "⚠️ تۆکێنی سەرەکی لە Vercel Environment Variables دەگۆڕێت، نەک لێرە.\n"
            "تۆکێنەکەت تۆمارکرا، تکایە لە Vercel گۆڕی.",
            reply_markup=KB_SYS(),
        )
        return

    if state == "confirm_clear_db":
        if txt == "✅ بەڵێ، پاک بکەرەوە":
            await db_del("users")
            await db_del("managed_bots")
            await db_del("bot_users")
            await db_del(f"users/{uid}/state")
            await update.message.reply_text("✅ داتابەیس پاک کرایەوە.", reply_markup=KB_SYS())
        else:
            await db_del(f"users/{uid}/state")
            await update.message.reply_text("↩️ هەڵوەشاندرایەوە.", reply_markup=KB_SYS())
        return

    if state == "confirm_restart":
        await db_del(f"users/{uid}/state")
        if txt == "✅ بەڵێ، ڕیستارت بکە":
            await update.message.reply_text("🔃 ڕیستارت ئەنجامدرا...\n\n⚠️ تێبینی: ڕیستارتی ڕاستەقینە پێویستی بە Vercel CLI ئەکات.", reply_markup=KB_SYS())
        else:
            await update.message.reply_text("↩️ هەڵوەشاندرایەوە.", reply_markup=KB_SYS())
        return

    # ── هەر شتێکی تر ──────────────────────────────────────────────────────
    await update.message.reply_text("تکایە لە کیبۆردی خوارەوە هەڵبژێرە 👇", reply_markup=kb_main(uid))


# ══════════════════════════════════════════════════════════════════════════════
# ── فەنکشنەکانی Owner
# ══════════════════════════════════════════════════════════════════════════════

async def owner_list_users(update: Update, full: bool = False):
    all_u = await db_get("users") or {}
    if not all_u:
        await update.message.reply_text("📭 هیچ بەکارهێنەرێک نییە.", reply_markup=KB_USERS())
        return
    lines = [f"👥 <b>لیستی بەکارهێنەران ({len(all_u)}):</b>\n"]
    for u_id, ud in list(all_u.items())[:50]:
        n  = html.escape(ud.get("name","ناسناو"))
        un = f"@{ud['username']}" if ud.get("username") else "—"
        lines.append(f"• <a href='tg://user?id={u_id}'>{n}</a> {un} <code>{u_id}</code>")
    if len(all_u) > 50:
        lines.append(f"\n... و {len(all_u)-50} بەکارهێنەری تری دیکە")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=KB_USERS())


async def owner_user_stats(update: Update):
    all_u  = await db_get("users")   or {}
    all_v  = await db_get("vip")     or {}
    all_bl = await db_get("blocked") or {}
    all_w  = await db_get("warnings") or {}
    admins = await db_get("admins")  or {}
    vip_ids= set(all_v.keys())
    msg    = (
        "📊 <b>ئامارەکانی بەکارهێنەران</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👥 کۆی بەکارهێنەران: <b>{len(all_u)}</b>\n"
        f"💎 VIPەکان: <b>{len(all_v)}</b>\n"
        f"👨‍💼 ئەدمینەکان: <b>{len(admins)}</b>\n"
        f"🚫 بلۆکەکان: <b>{len(all_bl)}</b>\n"
        f"⚠️ ئاگادارکراوەکان: <b>{len(all_w)}</b>\n"
        f"👤 نا-VIP: <b>{len(all_u) - len([i for i in all_u if i in vip_ids])}</b>"
    )
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=KB_USERS())


async def owner_export_users(update: Update):
    all_u = await db_get("users") or {}
    lines = ["ID | ناو | یوزەر | کاتی دوایین چالاکی"]
    for u_id, ud in all_u.items():
        lines.append(f"{u_id} | {ud.get('name','')} | @{ud.get('username','')} | {ud.get('last_seen','')}")
    txt = "\n".join(lines)
    msg = f"📤 <b>لیستی بەکارهێنەران ({len(all_u)}):</b>\n\n<code>{html.escape(txt[:3500])}</code>"
    if len(all_u) > 60:
        msg += f"\n\n... و {len(all_u)-60} بەکارهێنەری دیکە"
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=KB_USERS())


async def owner_list_bots(update: Update, filter_status=None):
    all_b = await db_get("managed_bots") or {}
    if filter_status:
        all_b = {k:v for k,v in all_b.items() if v.get("status") == filter_status}
    if not all_b:
        await update.message.reply_text("📭 هیچ بۆتێک نییە.", reply_markup=KB_BOTS())
        return
    lines = [f"🤖 <b>بۆتەکان ({len(all_b)}):</b>\n"]
    for bid, bd in list(all_b.items())[:40]:
        st  = "🟢" if bd.get("status") == "running" else "🔴"
        own = bd.get("owner","؟")
        bu  = await db_get(f"bot_users/{bid}") or {}
        lines.append(f"{st} @{bd.get('bot_username','—')}  👥{len(bu)}  خاوەن:<code>{own}</code>  ID:<code>{bid}</code>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=KB_BOTS())


async def owner_bot_stats(update: Update):
    all_b = await db_get("managed_bots") or {}
    run   = sum(1 for v in all_b.values() if v.get("status") == "running")
    total_users = 0
    for bid in all_b:
        bu = await db_get(f"bot_users/{bid}") or {}
        total_users += len(bu)
    msg = (
        "📊 <b>ئامارەکانی بۆتەکان</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 کۆی بۆتەکان: <b>{len(all_b)}</b>\n"
        f"🟢 چالاک: <b>{run}</b>\n"
        f"🔴 ڕاگیراو: <b>{len(all_b)-run}</b>\n"
        f"👥 کۆی بەکارهێنەران: <b>{total_users}</b>"
    )
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=KB_BOTS())


async def owner_all_bots_action(update: Update, new_status: str):
    all_b = await db_get("managed_bots") or {}
    count = 0
    for bid, bd in all_b.items():
        bd["status"] = new_status
        await db_put(f"managed_bots/{bid}", bd)
        count += 1
    icon = "🟢" if new_status == "running" else "🔴"
    await update.message.reply_text(f"{icon} <b>{count}</b> بۆت {('دەستی پێکرد' if new_status=='running' else 'وەستاندرا')}.", parse_mode="HTML", reply_markup=KB_BOTS())


async def owner_list_vips(update: Update):
    all_v = await db_get("vip") or {}
    if not all_v:
        await update.message.reply_text("📭 هیچ VIPێک نییە.", reply_markup=KB_VIP())
        return
    lines = [f"💎 <b>لیستی VIPەکان ({len(all_v)}):</b>\n"]
    for v_id, vd in list(all_v.items())[:40]:
        exp = vd.get("expires","نییە")
        lines.append(f"• <code>{v_id}</code> ⏰ {exp}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=KB_VIP())


async def owner_vip_stats(update: Update):
    all_v = await db_get("vip") or {}
    life  = sum(1 for v in all_v.values() if v.get("expires") == "lifetime")
    timed = len(all_v) - life
    msg   = (
        "📊 <b>ئامارەکانی VIP</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"💎 کۆی VIPەکان: <b>{len(all_v)}</b>\n"
        f"♾ هەمیشەیی: <b>{life}</b>\n"
        f"⏰ کاتی دیاریکراو: <b>{timed}</b>"
    )
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=KB_VIP())


async def owner_list_blocked(update: Update):
    all_bl = await db_get("blocked") or {}
    if not all_bl:
        await update.message.reply_text("📭 هیچ بلۆکێک نییە.", reply_markup=KB_SEC())
        return
    lines = [f"🚫 <b>بلۆکەکان ({len(all_bl)}):</b>\n"]
    for bid in list(all_bl.keys())[:40]:
        lines.append(f"• <code>{bid}</code>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=KB_SEC())


async def owner_list_warned(update: Update):
    all_w = await db_get("warnings") or {}
    if not all_w:
        await update.message.reply_text("📭 هیچ ئاگادارکراوێک نییە.", reply_markup=KB_SEC())
        return
    lines = [f"⚠️ <b>ئاگادارکراوەکان ({len(all_w)}):</b>\n"]
    for w_id, cnt in list(all_w.items())[:40]:
        lines.append(f"• <code>{w_id}</code> — ⚠️ {cnt} جار")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=KB_SEC())


async def owner_toggle_alert_mode(update: Update, uid: int):
    cur = await db_get("system/alert_mode") or False
    await db_put("system/alert_mode", not cur)
    state = "چالاک ✅" if not cur else "لەکارخراو ❌"
    await update.message.reply_text(f"🛡 مۆدی ئاگادارکردنەوە: <b>{state}</b>", parse_mode="HTML", reply_markup=KB_SEC())


async def owner_list_channels(update: Update):
    main_ch = await db_get("system/channel") or CHANNEL_USER
    req_chs = await db_get("system/req_channels") or {}
    fj      = await db_get("system/force_join") or False
    msg     = (
        f"‏📢 <b>زانیاری جۆینی ناچاری</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📢 کانالی سەرەکی بۆتەکان: @{main_ch}\n"
        f"🔔 دۆخی جۆینی ناچاری: <b>{'✅ چالاک' if fj else '❌ لەکارخراو'}</b>\n\n"
        f"📋 <b>کانالە داواکراوەکان ({len(req_chs)}):</b>\n"
    )
    if req_chs:
        for i, ch in enumerate(req_chs, 1):
            msg += f"  {i}. 🔗 @{ch} — <a href='https://t.me/{ch}'>لینک</a>\n"
    else:
        msg += "  📭 هیچ کانالێک زیادنەکراوە\n"
    msg += "\n💡 جۆینی ناچاری کاردەکات کاتێک بەکارهێنەر /start بکات"
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=KB_CHAN())


async def owner_channel_stats(update: Update):
    req_chs = await db_get("system/req_channels") or {}
    fj      = await db_get("system/force_join")   or False
    all_u   = await db_get("users") or {}
    msg     = (
        f"‏📊 <b>ئامارەکانی جۆینی ناچاری</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🔔 دۆخ: <b>{'✅ چالاک' if fj else '❌ لەکارخراو'}</b>\n"
        f"📋 کانالە داواکراوەکان: <b>{len(req_chs)}</b>\n"
        f"👥 کۆی بەکارهێنەران: <b>{len(all_u)}</b>\n\n"
        f"📌 کاتێک چالاکە: هەر بەکارهێنەرێک /start بکات، پشکنینی دەکرێت"
    )
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=KB_CHAN())


# ── فەنکشنەکانی ئەدمین ───────────────────────────────────────────────────────
async def owner_list_admins(update: Update):
    admins = await db_get("admins") or {}
    if not admins:
        await update.message.reply_text("📭 هیچ ئەدمینێک نییە.", reply_markup=KB_ADMINS())
        return
    lines = [f"‏👨‍💼 <b>لیستی ئەدمینەکان ({len(admins)}):</b>\n"]
    for a_id, ad in list(admins.items())[:40]:
        name = html.escape(ad.get("name","ناسناو"))
        date = ad.get("date","نییە")
        lines.append(f"• <a href='tg://user?id={a_id}'>{name}</a> <code>{a_id}</code> — زیادکرا: {date}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=KB_ADMINS())


async def owner_admin_stats(update: Update):
    admins = await db_get("admins") or {}
    msg = (
        f"‏📊 <b>ئامارەکانی ئەدمینەکان</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👨‍💼 کۆی ئەدمینەکان: <b>{len(admins)}</b>\n"
        f"👑 خاوەنی سیستەم: <b>1</b> (سەرەکی)"
    )
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=KB_ADMINS())


# ── فەنکشنەکانی ئاگادارکردنەوە ──────────────────────────────────────────────
async def owner_notif_history(update: Update):
    hist = await db_get("system/notif_history") or []
    if not hist:
        await update.message.reply_text("📭 هیچ مێژووی ئاگادارکردنەوەیەک نییە.", reply_markup=KB_NOTIF())
        return
    if isinstance(hist, dict): hist = list(hist.values())
    lines = [f"‏📋 <b>مێژووی ئاگادارکردنەوە:</b>\n"]
    for h in hist[:15]:
        tp   = h.get("type","—")
        sent = h.get("sent",0)
        fail = h.get("fail",0)
        tm   = h.get("time","—")
        lines.append(f"🔔 {tm} | {tp} | ✅{sent} ❌{fail}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=KB_NOTIF())


async def show_user_notifications(update: Update, uid: int):
    """نیشاندانی ئاگادارکردنەوەکانی بەکارهێنەر"""
    notif_on = await db_get("system/notifications_enabled")
    user_notif = await db_get(f"users/{uid}/notifications_off") or False
    msg = (
        "🔔 <b>ئاگادارکردنەوەکانت</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📢 دۆخی سیستەم: {'✅ چالاک' if notif_on else '❌ لەکارخراو'}\n"
        f"👤 ئاگادارکردنەوەی تۆ: {'❌ کوژاوە' if user_notif else '✅ چالاک'}\n"
    )
    kb = IKM([[IKB("🔕 کوژاندنەوەی ئاگادارکردنەوەم" if not user_notif else "🔔 چالاككردنی ئاگادارکردنەوەم", "user_notif_off" if not user_notif else "user_notif_on")], [IKB("🔙 گەڕانەوە بۆ سەرەتا", "back_home")]])
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=kb)


async def owner_sys_info(update: Update):
    all_b  = await db_get("managed_bots") or {}
    all_u  = await db_get("users")         or {}
    admins = await db_get("admins")        or {}
    run    = sum(1 for v in all_b.values() if v.get("status") == "running")
    purl   = await db_get("system/project_url") or PROJECT_URL or "نەدۆزرایەوە"
    fj     = await db_get("system/force_join")  or False
    am     = await db_get("system/alert_mode")  or False
    notif  = await db_get("system/notifications_enabled") or False
    msg    = (
        f"‏⚙️ <b>زانیاری سیستەم</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 PROJECT URL: <code>{purl}</code>\n"
        f"👥 بەکارهێنەران: <b>{len(all_u)}</b>\n"
        f"🤖 بۆتەکان: <b>{len(all_b)}</b>  (🟢{run})\n"
        f"👨‍💼 ئەدمینەکان: <b>{len(admins)}</b>\n"
        f"📢 جۆینی ناچاری: <b>{'چالاک' if fj else 'لەکارخراو'}</b>\n"
        f"🛡 مۆدی ئاگادارکردنەوە: <b>{'چالاک' if am else 'لەکارخراو'}</b>\n"
        f"🔔 ئاگادارکردنەوەکان: <b>{'چالاک' if notif else 'لەکارخراو'}</b>\n"
        f"⏰ کاتی ئێستا: <b>{now_str()}</b>"
    )
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=KB_SYS())


async def owner_refresh_all_webhooks(update: Update):
    all_b = await db_get("managed_bots") or {}
    sm    = await update.message.reply_text(f"⏳ نوێکردنەوەی {len(all_b)} وەبهووک...")
    ok=fail=0
    safe  = (PROJECT_URL or "").rstrip('/')
    for bid, bd in all_b.items():
        if bd.get("status") != "running": continue
        token = bd.get("token","")
        if not token: continue
        r = await send_tg(token,"setWebhook",{"url":f"{safe}/api/bot/{token}","allowed_updates":["message","channel_post","callback_query"]})
        if r.get("ok"): ok+=1
        else: fail+=1
        await asyncio.sleep(0.1)
    await sm.edit_text(f"✅ وەبهووک نوێکرایەوە!\n✅ سەرکەوتوو: {ok}  ❌ هەڵە: {fail}", reply_markup=KB_SYS())


async def owner_backup_db(update: Update):
    all_b  = await db_get("managed_bots") or {}
    all_u  = await db_get("users")         or {}
    all_v  = await db_get("vip")           or {}
    admins = await db_get("admins")        or {}
    backup = {
        "time":         now_str(),
        "users_count":  len(all_u),
        "bots_count":   len(all_b),
        "vip_count":    len(all_v),
        "admin_count":  len(admins),
        "bot_usernames":[v.get("bot_username","") for v in all_b.values()],
    }
    msg = (
        "💾 <b>پشتگیری داتابەیس</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ کات: {backup['time']}\n"
        f"👥 بەکارهێنەران: {backup['users_count']}\n"
        f"🤖 بۆتەکان: {backup['bots_count']}\n"
        f"💎 VIPەکان: {backup['vip_count']}\n"
        f"👨‍💼 ئەدمینەکان: {backup['admin_count']}\n"
        f"🤖 ناوی بۆتەکان:\n<code>{', '.join(backup['bot_usernames'][:20])}</code>"
    )
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=KB_SYS())


async def owner_show_logs(update: Update):
    logs = await db_get("system/logs") or []
    if not logs:
        await update.message.reply_text("📭 هیچ لۆگێک نییە.", reply_markup=KB_SYS())
        return
    if isinstance(logs, dict): logs = list(logs.values())
    lines = [f"‏📋 <b>دوایین لۆگەکان:</b>\n"]
    for log in logs[:15]:
        lines.append(f"• {log}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=KB_SYS())


async def owner_broadcast_history(update: Update):
    hist = await db_get("system/bc_history") or []
    if not hist:
        await update.message.reply_text("📭 هیچ مێژووی بڵاوکردنەوە نییە.", reply_markup=KB_MSG())
        return
    if isinstance(hist, dict): hist = list(hist.values())
    lines = [f"‏📜 <b>مێژووی بڵاوکردنەوە:</b>\n"]
    for h in hist[:15]:
        tp   = h.get("type","—")
        sent = h.get("sent",0)
        fail = h.get("fail",0)
        tm   = h.get("time","—")
        lines.append(f"📤 {tm} | {tp} | ✅{sent} ❌{fail}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=KB_MSG())


# ══════════════════════════════════════════════════════════════════════════════
# ── چالاككردنی تۆکێن
# ══════════════════════════════════════════════════════════════════════════════
async def activate_token(update: Update, uid: int, token: str):
    sm = await update.message.reply_text("⏳ خەریکی پشکنین و چالاككردنم...")
    try:
        res = await send_tg(token,"getMe",{})
        if not res.get("ok"):
            await sm.edit_text("❌ تۆکێنەکە هەڵەیە یان کار ناکات.")
            return
        bi  = res["result"]
        bid = str(bi["id"])
        bun = bi["username"]
        bnm = bi["first_name"]
        if await db_get(f"managed_bots/{bid}"):
            await sm.edit_text(f"⚠️ بۆتی @{bun} پێشتر تۆمارکراوە!")
            return
        safe = (PROJECT_URL or "").rstrip('/')
        wh   = await send_tg(token,"setWebhook",{"url":f"{safe}/api/bot/{token}","allowed_updates":["message","channel_post","callback_query"]})
        if not wh.get("ok"):
            await sm.edit_text("❌ هەڵەیەک ڕوویدا لە بەستنەوەی وەبهووک.")
            return
        # جۆری بۆت لە پێشتر هەڵبژێردرا
        chosen_type = await db_get(f"users/{uid}/pending_bot_type") or "reaction"
        await db_del(f"users/{uid}/pending_bot_type")

        await db_put(f"managed_bots/{bid}",{
            "token":token,"owner":uid,"bot_username":bun,
            "bot_name":bnm,"status":"running","type":chosen_type,"welcome_msg":"",
            "created": now_str(), "notif_enabled": True,
        })
        await db_del(f"users/{uid}/state")
        await db_put(f"users/{uid}/selected_bot", bid)
        R = "\u200f"
        vip_stat  = "💎 VIP" if await is_vip(uid) else "👤 ئاسایی"
        if chosen_type == "reaction":
            type_lbl  = "🍓 بۆتی ڕیاکشن"
            type_hint = f"{R}٥. بۆ هەموو نامەیەک ئیموجی دەنێرێت 🍓"
        elif chosen_type == "weather":
            type_lbl  = "🌤️ بۆتی کەش و هەوا"
            type_hint = f"{R}٥. /start بنووسە، ناوچە و شار هەڵبژێرە 🌤️"
        else:
            type_lbl  = "🪪 بۆتی زانیاری"
            type_hint = f"{R}٥. /id یان /info بنووسە تا زانیاری بەکارهێنەر ببینیت 🪪"
        await sm.edit_text(
            f"{R}🎉 <b>پیرۆزە! بۆتەکەت سەرکەوتووانە دروست کرا</b>\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}🤖 <b>ناوی بۆت:</b> {html.escape(bnm)}\n"
            f"{R}🔗 <b>یوزەرنەیم:</b> @{bun}\n"
            f"{R}🆔 <b>ID ی بۆت:</b> <code>{bid}</code>\n"
            f"{R}🎯 <b>جۆر:</b> {type_lbl}\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}👑 <b>خاوەن:</b> <a href='tg://user?id={uid}'>ئێتۆ</a>\n"
            f"{R}🎖 <b>دۆخی ئێتۆ:</b> {vip_stat}\n"
            f"{R}⏰ <b>کاتی دروستکردن:</b> {now_str()}\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}🟢 <b>دۆخ:</b> چالاک و ئامادەیە\n"
            f"{R}🔔 <b>ئاگادارکردنەوە:</b> ✅ چالاک\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}📌 <b>هەنگاوەکان:</b>\n"
            f"{R}١. بۆتەکەت زیاد بکە بۆ گروپ/کانالەکەت\n"
            f"{R}٢. ئادمینی تەواوی پێ بدە\n"
            f"{R}٣. لە '📂 بۆتەکانم' کۆنترۆڵی بکە\n"
            f"{R}٤. ئاگادارکردنەوە چالاکە 🔔\n"
            f"{type_hint}",
            parse_mode="HTML",
        )
        await update.message.reply_text(
            f"{R}👇 بۆ کۆنترۆڵ:",
            parse_mode="HTML", reply_markup=kb_control(uid)
        )
    except Exception as e:
        logger.error(f"activate: {e}")
        await sm.edit_text(f"❌ هەڵەیەکی چاوەڕواننەکراو:\n<code>{html.escape(str(e))}</code>", parse_mode="HTML")


# ══════════════════════════════════════════════════════════════════════════════
# ── سڕینەوەی بۆت
# ══════════════════════════════════════════════════════════════════════════════
async def do_delete_bot(update: Update, uid: int, bid: str, back_kb=None):
    info  = await db_get(f"managed_bots/{bid}") or {}
    un    = info.get("bot_username","ناسناو")
    token = info.get("token","")
    if token:
        try: await send_tg(token,"deleteWebhook",{})
        except: pass
    await db_del(f"managed_bots/{bid}")
    await db_del(f"users/{uid}/selected_bot")
    await db_del(f"users/{uid}/state")
    kb = back_kb if back_kb else kb_main(uid)
    await update.message.reply_text(f"🗑 <b>بۆتی @{un} بە تەواوی سڕایەوە!</b>", parse_mode="HTML", reply_markup=kb)


# ══════════════════════════════════════════════════════════════════════════════
# ██  بۆتی کەش و هەوا — داتا و فانکشنەکان
# ══════════════════════════════════════════════════════════════════════════════

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

KURDISTAN_CITIES = {
    "iraq": {
        "name": "🇮🇶 کوردستانی عێراق",
        "cities": {
            "هەولێر":      {"lat": 36.1901, "lon": 44.0091, "emoji": "🏛️"},
            "سلێمانی":     {"lat": 35.5573, "lon": 45.4352, "emoji": "🏔️"},
            "دهۆک":        {"lat": 36.8674, "lon": 42.9462, "emoji": "🌿"},
            "کەرکووک":     {"lat": 35.4681, "lon": 44.3922, "emoji": "🛢️"},
            "زاخۆ":        {"lat": 37.1446, "lon": 42.6787, "emoji": "🌉"},
            "ئامێدی":      {"lat": 37.0926, "lon": 43.4878, "emoji": "🏰"},
            "عەقرە":       {"lat": 36.7451, "lon": 43.8928, "emoji": "⛰️"},
            "ڕانیە":       {"lat": 36.2580, "lon": 44.7156, "emoji": "🌊"},
            "شاقڵاوە":     {"lat": 36.4072, "lon": 44.3225, "emoji": "🌸"},
            "دوکان":       {"lat": 35.9581, "lon": 44.9612, "emoji": "💧"},
            "دەربەندیخان": {"lat": 35.1118, "lon": 45.6959, "emoji": "🌁"},
            "پێنجوێن":     {"lat": 35.6217, "lon": 45.9425, "emoji": "❄️"},
            "حەڵەبجە":     {"lat": 35.1763, "lon": 45.9862, "emoji": "🌹"},
            "سۆران":       {"lat": 36.6538, "lon": 44.5441, "emoji": "🏕️"},
            "ڕەواندوز":    {"lat": 36.6130, "lon": 44.5263, "emoji": "🌈"},
            "خانەقین":     {"lat": 34.3477, "lon": 45.3786, "emoji": "🌻"},
            "قەلادزێ":     {"lat": 36.1820, "lon": 45.1314, "emoji": "🏯"},
            "چۆمان":       {"lat": 36.6333, "lon": 44.8833, "emoji": "🏔️"},
            "سیدەکان":     {"lat": 36.6667, "lon": 44.5333, "emoji": "🌲"},
            "بارزان":      {"lat": 36.9167, "lon": 43.9833, "emoji": "🦅"},
        }
    },
    "iran": {
        "name": "🇮🇷 ڕۆژهەڵاتی کوردستان",
        "cities": {
            "مەهاباد":     {"lat": 36.7631, "lon": 45.7228, "emoji": "🌊"},
            "کرماشان":     {"lat": 34.3142, "lon": 47.0650, "emoji": "🏛️"},
            "سەنەندەج":    {"lat": 35.3219, "lon": 47.0050, "emoji": "🏔️"},
            "بانە":        {"lat": 35.9977, "lon": 45.8854, "emoji": "🛍️"},
            "مریوان":      {"lat": 35.5230, "lon": 46.1748, "emoji": "💦"},
            "سەقز":        {"lat": 36.2459, "lon": 46.2685, "emoji": "🌾"},
            "ئۆشنۆ":       {"lat": 37.0409, "lon": 45.0981, "emoji": "🌺"},
            "پیرانشار":    {"lat": 36.6981, "lon": 45.1382, "emoji": "⛰️"},
            "سەرداشت":     {"lat": 36.1558, "lon": 45.4772, "emoji": "🌲"},
            "هەورامان":    {"lat": 35.2010, "lon": 46.4400, "emoji": "🏰"},
        }
    },
    "turkey": {
        "name": "🇹🇷 باکووری کوردستان",
        "cities": {
            "دیاربەکر":    {"lat": 37.9144, "lon": 40.2306, "emoji": "🏰"},
            "مەردین":      {"lat": 37.3212, "lon": 40.7245, "emoji": "🕌"},
            "وان":         {"lat": 38.4891, "lon": 43.4089, "emoji": "💧"},
            "ئەگری":       {"lat": 39.7191, "lon": 43.0503, "emoji": "🌋"},
            "بیتلیس":      {"lat": 38.3938, "lon": 42.1232, "emoji": "🏔️"},
            "موش":         {"lat": 38.7432, "lon": 41.4923, "emoji": "🌾"},
            "سیرت":        {"lat": 37.9270, "lon": 41.9400, "emoji": "🌿"},
            "شرناق":       {"lat": 37.5164, "lon": 42.4611, "emoji": "🦅"},
            "بینگۆل":      {"lat": 38.8854, "lon": 40.4980, "emoji": "🌸"},
            "تونجەلی":     {"lat": 39.1079, "lon": 39.5477, "emoji": "🌊"},
        }
    },
    "syria": {
        "name": "🇸🇾 ڕۆژاوای کوردستان",
        "cities": {
            "قامیشلۆ":     {"lat": 37.0522, "lon": 41.2268, "emoji": "🌟"},
            "ئەفرین":      {"lat": 36.5127, "lon": 36.8686, "emoji": "🫒"},
            "کۆبانی":      {"lat": 36.8890, "lon": 38.3568, "emoji": "🕊️"},
            "دیریک":       {"lat": 37.1667, "lon": 42.1333, "emoji": "🌾"},
            "سەرەکانی":    {"lat": 36.8489, "lon": 40.0709, "emoji": "💦"},
            "حەسەکە":      {"lat": 36.4840, "lon": 40.7489, "emoji": "🌴"},
            "تل ئەبیەد":   {"lat": 36.6980, "lon": 38.9558, "emoji": "🌵"},
            "مانبج":       {"lat": 36.5224, "lon": 37.9461, "emoji": "🏙️"},
            "کۆبانی":      {"lat": 36.8890, "lon": 38.3568, "emoji": "🕊️"},
            "دەیرەززۆر":   {"lat": 35.3360, "lon": 40.1419, "emoji": "🌊"},
        }
    }
}

WMO_CODES = {
    0:("ئاسمانی پاک","☀️"),1:("زۆربەی پاک","🌤️"),2:("کەمێک هەور","⛅"),
    3:("هەوری تەواو","☁️"),45:("تەمووک","🌁"),48:("تەمووکی بەستراو","🌫️"),
    51:("فیسکەی سووک","🌦️"),53:("فیسکە","🌦️"),55:("فیسکەی توند","🌧️"),
    61:("بارانی سووک","🌦️"),63:("باران","🌧️"),65:("بارانی توند","🌧️"),
    71:("بەفری سووک","🌨️"),73:("بەفر","❄️"),75:("بەفری توند","❄️"),
    80:("شەقامی سووک","🌦️"),81:("شەقام","🌧️"),82:("شەقامی توند","⛈️"),
    95:("گەڕوگوڵ","⛈️"),96:("گەڕوگوڵ بە تەرزە","⛈️"),99:("گەڕوگوڵی توند","⛈️"),
}
WEATHER_WEEKDAYS = {0:"دووشەممە",1:"سێشەممە",2:"چوارشەممە",
                    3:"پێنجشەممە",4:"هەینی",5:"شەممە",6:"یەکشەممە"}
WEATHER_CURRENT_FIELDS = [
    "temperature_2m","relative_humidity_2m","apparent_temperature",
    "weather_code","cloud_cover","pressure_msl","wind_speed_10m",
    "wind_direction_10m","wind_gusts_10m","visibility","uv_index","dew_point_2m","precipitation"
]
WEATHER_DAILY_FIELDS = [
    "weather_code","temperature_2m_max","temperature_2m_min",
    "sunrise","sunset","uv_index_max","precipitation_sum",
    "wind_speed_10m_max","wind_direction_10m_dominant"
]
WEATHER_HOURLY_FIELDS = [
    "temperature_2m","relative_humidity_2m","weather_code",
    "wind_speed_10m","precipitation","apparent_temperature"
]

def wmo_kurd(code: int) -> tuple:
    return WMO_CODES.get(code, ("نەزانراو","🌡️"))

def weather_wind_dir(deg: float) -> str:
    dirs = ["باکوور ⬆️","باکوور-ڕۆژهەڵات ↗️","ڕۆژهەڵات ➡️","باشوور-ڕۆژهەڵات ↘️",
            "باشوور ⬇️","باشوور-ڕۆژئاوا ↙️","ڕۆژئاوا ⬅️","باکوور-ڕۆژئاوا ↖️"]
    return dirs[round(deg / 45) % 8]

def weather_uv(uv: float) -> str:
    if uv < 3:  return f"{uv:.0f} 🟢"
    if uv < 6:  return f"{uv:.0f} 🟡"
    if uv < 8:  return f"{uv:.0f} 🟠"
    if uv < 11: return f"{uv:.0f} 🔴"
    return f"{uv:.0f} 🟣"

def fmt_weather_current(data: dict, city: str, em: str) -> str:
    c = data["current"]; d = data["daily"]
    desc, demoji = wmo_kurd(c["weather_code"])
    temp   = c["temperature_2m"];  feels = c["apparent_temperature"]
    hum    = c["relative_humidity_2m"]; dew = c["dew_point_2m"]
    press  = c["pressure_msl"]; cloud = c["cloud_cover"]
    vis    = (c.get("visibility") or 0) / 1000
    wind   = c["wind_speed_10m"]; wdir = c["wind_direction_10m"]
    gust   = c["wind_gusts_10m"]; precip = c.get("precipitation") or 0
    uv     = c.get("uv_index") or 0
    t_max  = d["temperature_2m_max"][0]; t_min = d["temperature_2m_min"][0]
    sr_raw = d["sunrise"][0]; sr = sr_raw.split("T")[1] if "T" in sr_raw else sr_raw
    ss_raw = d["sunset"][0];  ss = ss_raw.split("T")[1] if "T" in ss_raw else ss_raw
    now    = datetime.now().strftime("%H:%M  %Y/%m/%d")
    R = "\u200f"
    return (
        f"{R}{em} <b>{city}</b>\n"
        f"{R}━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{R}{demoji} <b>هەلومەرج:</b> {desc}\n"
        f"{R}🌡️ <b>گەرمی:</b> <code>{temp:.1f}°C</code>  |  🤔 <b>هەست:</b> <code>{feels:.1f}°C</code>\n"
        f"{R}🔼 <b>زیاترین:</b> <code>{t_max:.1f}°C</code>   🔽 <b>کەمترین:</b> <code>{t_min:.1f}°C</code>\n\n"
        f"{R}💧 <b>شێ:</b> <code>{hum}%</code>   🌡️ <b>خاڵی شەودە:</b> <code>{dew:.1f}°C</code>\n"
        f"{R}☁️ <b>هەور:</b> <code>{cloud}%</code>   👁️ <b>بینراو:</b> <code>{vis:.1f} کم</code>\n"
        f"{R}📊 <b>کڕەلا:</b> <code>{press:.0f} hPa</code>\n\n"
        f"{R}🌬️ <b>با:</b> <code>{wind:.1f} کم/س</code> — {weather_wind_dir(wdir)}\n"
        f"{R}💨 <b>بارزەی با:</b> <code>{gust:.1f} کم/س</code>\n"
        f"{R}🌧️ <b>باران:</b> <code>{precip:.1f} مم</code>\n"
        f"{R}☀️ <b>UV:</b> {weather_uv(uv)}\n\n"
        f"{R}🌅 <b>هەتاوهەڵهاتن:</b> <code>{sr}</code>   🌇 <b>هەتاوچوون:</b> <code>{ss}</code>\n"
        f"{R}🕐 <b>ئێستا:</b> <code>{now}</code>"
    )

def fmt_weather_forecast(data: dict, city: str, em: str, days: int) -> str:
    d = data["daily"]
    R = "\u200f"
    msg = f"{R}{em} <b>پێشبینی {days} ڕۆژ — {city}</b>\n{R}━━━━━━━━━━━━━━━━━━━━\n\n"
    for i in range(min(days, len(d["weather_code"]))):
        dt      = datetime.strptime(d["time"][i], "%Y-%m-%d")
        weekday = WEATHER_WEEKDAYS[dt.weekday()]
        date_f  = dt.strftime("%d/%m")
        desc, demoji = wmo_kurd(d["weather_code"][i])
        t_max   = d["temperature_2m_max"][i]; t_min = d["temperature_2m_min"][i]
        precip  = d["precipitation_sum"][i] or 0
        wind    = d["wind_speed_10m_max"][i]
        uv      = d["uv_index_max"][i] or 0
        sr_raw  = d["sunrise"][i]; sr = sr_raw.split("T")[1] if "T" in sr_raw else sr_raw
        ss_raw  = d["sunset"][i];  ss = ss_raw.split("T")[1] if "T" in ss_raw else ss_raw
        today_l = " <b>(ئەمڕۆ)</b>" if i == 0 else ""
        msg += (f"{R}📅 <b>{weekday} ({date_f})</b>{today_l}\n"
                f"{R}   {demoji} {desc}\n"
                f"{R}   🌡️ <code>{t_min:.0f}°C ~ {t_max:.0f}°C</code>\n"
                f"{R}   🌧️<code>{precip:.1f}مم</code>  🌬️<code>{wind:.0f}کم/س</code>  ☀️UV:<code>{uv:.0f}</code>\n"
                f"{R}   🌅<code>{sr}</code> — 🌇<code>{ss}</code>\n\n")
    return msg.strip()

def fmt_weather_hourly(data: dict, city: str, em: str) -> str:
    hourly = data.get("hourly", {})
    times  = hourly.get("time", [])
    temps  = hourly.get("temperature_2m", [])
    wcodes = hourly.get("weather_code", [])
    winds  = hourly.get("wind_speed_10m", [])
    precs  = hourly.get("precipitation", [])
    humids = hourly.get("relative_humidity_2m", [])
    today  = datetime.now().strftime("%Y-%m-%d")
    R = "\u200f"
    msg   = f"{R}{em} <b>ساعاتانەی ئەمڕۆ — {city}</b>\n{R}━━━━━━━━━━━━━━━━━━━━\n\n"
    count = 0
    for i, t in enumerate(times):
        if not t.startswith(today): continue
        hour = t.split("T")[1][:5]
        if int(hour.split(":")[0]) % 3 != 0: continue
        temp = temps[i] if i < len(temps) else 0
        wc   = wcodes[i] if i < len(wcodes) else 0
        wind = winds[i]  if i < len(winds)  else 0
        prec = precs[i]  if i < len(precs)  else 0
        hum  = humids[i] if i < len(humids) else 0
        _, demi = wmo_kurd(wc)
        rain_str = f"  🌧️<code>{prec:.1f}مم</code>" if prec > 0 else ""
        msg += f"{R}🕐<code>{hour}</code> {demi}<code>{temp:.0f}°C</code> 💧<code>{hum}%</code> 🌬️<code>{wind:.0f}کم/س</code>{rain_str}\n"
        count += 1
    if count == 0:
        msg += "زانیاری ساعاتانە بەردەست نییە."
    return msg.strip()

def weather_kb_main() -> dict:
    rows = [[{"text": rd["name"], "callback_data": f"wfj_region_{rk}"}]
            for rk, rd in KURDISTAN_CITIES.items()]
    rows.append([{"text": "🏠 سەرەکی", "callback_data": "wfj_main"}])
    return {"inline_keyboard": rows}

def weather_kb_cities(rk: str) -> dict:
    cities = list(KURDISTAN_CITIES[rk]["cities"].keys())
    info   = KURDISTAN_CITIES[rk]["cities"]
    rows = []
    for i in range(0, len(cities), 2):
        row = [{"text": f"{info[c]['emoji']} {c}", "callback_data": f"wfj_city_{rk}_{c}"}
               for c in cities[i:i+2]]
        rows.append(row)
    rows.append([{"text": "◀️ گەڕانەوە", "callback_data": "wfj_main"}])
    return {"inline_keyboard": rows}

def weather_kb_options(rk: str, city: str) -> dict:
    return {"inline_keyboard": [
        [{"text": "🌡️ کەش و هەوای ئێستا",  "callback_data": f"wfj_w_{rk}_{city}"}],
        [{"text": "⏰ ساعاتانەی ئەمڕۆ",     "callback_data": f"wfj_h_{rk}_{city}"}],
        [{"text": "📅 پێشبینی ٣ ڕۆژ",       "callback_data": f"wfj_f3_{rk}_{city}"},
         {"text": "📅 پێشبینی ٧ ڕۆژ",       "callback_data": f"wfj_f7_{rk}_{city}"}],
        [{"text": "◀️ گەڕانەوە",             "callback_data": f"wfj_region_{rk}"},
         {"text": "🏠 سەرەکی",              "callback_data": "wfj_main"}],
    ]}

def weather_kb_back(rk: str) -> dict:
    return {"inline_keyboard": [[
        {"text": "◀️ گەڕانەوە", "callback_data": f"wfj_region_{rk}"},
        {"text": "🏠 سەرەکی",  "callback_data": "wfj_main"},
    ]]}

WEATHER_WELCOME = (
    "\u200f🌤️ <b>بۆتی کەش و هەوای کوردستان</b>\n"
    "\u200f━━━━━━━━━━━━━━━━━━━━\n\n"
    "\u200f🇮🇶 کوردستانی عێراق — ٢٠ شار\n"
    "\u200f🇮🇷 ڕۆژهەڵاتی کوردستان — ١٠ شار\n"
    "\u200f🇹🇷 باکووری کوردستان — ١٠ شار\n"
    "\u200f🇸🇾 ڕۆژاوای کوردستان — ١٠ شار\n\n"
    "\u200f👇 ناوچەیەکی هەڵبژێرە:"
)


# ══════════════════════════════════════════════════════════════════════════════
# ── بۆتی منداڵ (Child Bot)
# ══════════════════════════════════════════════════════════════════════════════
async def process_child_update(token: str, body: dict):
    try:
        bid  = token.split(":")[0]
        info = await db_get(f"managed_bots/{bid}")
        if not info or info.get("status") != "running": return

        bun  = info.get("bot_username","UnknownBot")
        bnm  = info.get("bot_name","Reaction Bot")
        wlcm = info.get("welcome_msg","")

        sys_photo   = await db_get("system/photo_url") or PHOTO_URL
        sys_chan    = await db_get("system/channel")   or CHANNEL_USER
        req_chs     = await db_get("system/req_channels") or {}
        fj          = await db_get("system/force_join") or False
        # جۆینی ناچاری تایبەت بۆ هەموو بۆتەکان (لە پانێلی سەرەکی)
        child_fj_on = await db_get("system/child_fj_enabled") or False
        child_fj_chs= await db_get("system/child_fj_channels") or {}
        # یەکگرتنەوەی هەر دوو لیست
        if child_fj_on and child_fj_chs:
            fj = True
            for ch in child_fj_chs:
                req_chs[ch] = True

        msg = body.get("message") or body.get("channel_post")

    # بۆ callback_query — پرۆسەسی تایبەت
        if body.get("callback_query"):
            cq       = body["callback_query"]
            cq_data  = cq.get("data","")
            cq_from  = cq.get("from",{})
            cq_uid   = cq_from.get("id")
            cq_msg   = cq.get("message",{})
            cq_chat  = cq_msg.get("chat",{}).get("id")
            cq_mid   = cq_msg.get("message_id")
            bot_type = info.get("type","reaction")
            
            # --- دەستپێکی کۆدی نوێی ڕیاکشن ---
            if bot_type == "reaction" and cq_data.startswith("react_"):
                async with httpx.AsyncClient(timeout=10) as c:
                    await c.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", json={"callback_query_id": cq["id"]})
                    
                    chat_settings = await db_get(f"bot_settings/{bid}/{cq_chat}") or {"mode": "random", "emojis": []}
                    
                    if cq_data.startswith("react_tg_"):
                        emo = cq_data.split("_")[2]
                        chat_settings["mode"] = "custom"
                        if emo in chat_settings["emojis"]: chat_settings["emojis"].remove(emo)
                        else: chat_settings["emojis"].append(emo)
                        await db_put(f"bot_settings/{bid}/{cq_chat}", chat_settings)
                        
                    elif cq_data == "react_rnd":
                        chat_settings["mode"] = "random"
                        chat_settings["emojis"] = []
                        await db_put(f"bot_settings/{bid}/{cq_chat}", chat_settings)
                        
                    elif cq_data == "react_done":
                        await c.post(f"https://api.telegram.org/bot{token}/deleteMessage", json={"chat_id": cq_chat, "message_id": cq_mid})
                        return

                    # دروستکردنەوەی کیبۆردی ئیمۆجییەکان (نمایشکردنی ٢٤ ئیمۆجی)
                    keys = []
                    row = []
                    for e in EMOJIS[:24]:
                        mark = "✅" if chat_settings.get("mode") == "custom" and e in chat_settings.get("emojis", []) else ""
                        row.append({"text": f"{e}{mark}", "callback_data": f"react_tg_{e}"})
                        if len(row) == 4:
                            keys.append(row)
                            row = []
                    rnd_mark = "✅" if chat_settings.get("mode") == "random" else ""
                    keys.append([{"text": f"🎲 هەڕەمەکی (Random) {rnd_mark}", "callback_data": "react_rnd"}])
                    keys.append([{"text": "✅ پاشەکەوتکردن و داخستن", "callback_data": "react_done"}])
                    
                    await c.post(f"https://api.telegram.org/bot{token}/editMessageReplyMarkup", json={
                        "chat_id": cq_chat, "message_id": cq_mid,
                        "reply_markup": {"inline_keyboard": keys}
                    })
                return
            # --- کۆتایی کۆدی نوێی ڕیاکشن ---
            
            if bot_type == "weather" and cq_data.startswith("wfj_"):
                async with httpx.AsyncClient(timeout=10) as c:
                    # پەسەندکردنی callback
                    await c.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery",
                                 json={"callback_query_id": cq["id"]})

                    if cq_data in ("wfj_main", "wfj_refresh"):
                        await c.post(f"https://api.telegram.org/bot{token}/editMessageText", json={
                            "chat_id": cq_chat, "message_id": cq_mid,
                            "text": WEATHER_WELCOME, "parse_mode": "HTML",
                            "reply_markup": weather_kb_main(),
                        })
                        return

                    if cq_data.startswith("wfj_region_"):
                        rk = cq_data[11:]
                        region = KURDISTAN_CITIES.get(rk)
                        if not region: return
                        cnt = len(region["cities"])
                        R = "\u200f"
                        await c.post(f"https://api.telegram.org/bot{token}/editMessageText", json={
                            "chat_id": cq_chat, "message_id": cq_mid,
                            "text": f"{R}{region['name']}\n{R}━━━━━━━━━━━━━━━━━━━━\n\n{R}📍 {cnt} شار بەردەستە.\n\n{R}شارێک هەڵبژێرە:",
                            "parse_mode": "HTML",
                            "reply_markup": weather_kb_cities(rk),
                        })
                        return

                    if cq_data.startswith("wfj_city_"):
                        _, _, rk, city = cq_data.split("_", 3)
                        region = KURDISTAN_CITIES.get(rk)
                        if not region: return
                        ci = region["cities"].get(city)
                        if not ci: return
                        R = "\u200f"
                        await c.post(f"https://api.telegram.org/bot{token}/editMessageText", json={
                            "chat_id": cq_chat, "message_id": cq_mid,
                            "text": f"{R}{ci['emoji']} <b>{city}</b>\n{R}━━━━━━━━━━━━━━━━━━━━\n\n{R}چی دەتەوێت ببینیت؟",
                            "parse_mode": "HTML",
                            "reply_markup": weather_kb_options(rk, city),
                        })
                        return

                    for prefix, mode in [("wfj_w_","current"),("wfj_h_","hourly"),
                                          ("wfj_f3_","forecast3"),("wfj_f7_","forecast7")]:
                        if cq_data.startswith(prefix):
                            rest = cq_data[len(prefix):]
                            rk, city = rest.split("_", 1)
                            region = KURDISTAN_CITIES.get(rk)
                            if not region: return
                            ci = region["cities"].get(city)
                            if not ci: return
                            await c.post(f"https://api.telegram.org/bot{token}/editMessageText", json={
                                "chat_id": cq_chat, "message_id": cq_mid,
                                "text": "\u200f⏳ <b>زانیاری وەردەگیرێت...</b>",
                                "parse_mode": "HTML",
                            })
                            try:
                                params = {
                                    "latitude": ci["lat"], "longitude": ci["lon"],
                                    "current": WEATHER_CURRENT_FIELDS,
                                    "daily": WEATHER_DAILY_FIELDS,
                                    "timezone": "auto", "forecast_days": 7,
                                    "wind_speed_unit": "kmh",
                                }
                                if mode == "hourly":
                                    params["hourly"] = WEATHER_HOURLY_FIELDS
                                wr = await c.get(OPEN_METEO_URL, params=params, timeout=15)
                                wr.raise_for_status()
                                wdata = wr.json()
                            except:
                                await c.post(f"https://api.telegram.org/bot{token}/editMessageText", json={
                                    "chat_id": cq_chat, "message_id": cq_mid,
                                    "text": "\u200f❌ <b>هەڵە:</b> زانیاری نەدۆزرایەوە.",
                                    "parse_mode": "HTML",
                                    "reply_markup": weather_kb_back(rk),
                                })
                                return
                            em = ci["emoji"]
                            if mode == "current":   wmsg = fmt_weather_current(wdata, city, em)
                            elif mode == "hourly":  wmsg = fmt_weather_hourly(wdata, city, em)
                            elif mode == "forecast3": wmsg = fmt_weather_forecast(wdata, city, em, 3)
                            else:                   wmsg = fmt_weather_forecast(wdata, city, em, 7)
                            await c.post(f"https://api.telegram.org/bot{token}/editMessageText", json={
                                "chat_id": cq_chat, "message_id": cq_mid,
                                "text": wmsg, "parse_mode": "HTML",
                                "reply_markup": weather_kb_back(rk),
                            })
                            return
            return  # callback_query تر نادەستێنین

        if not msg: return

        chat_id    = msg["chat"]["id"]
        message_id = msg["message_id"]
        txt        = msg.get("text","")

        from_user = msg.get("from") or msg.get("sender_chat") or {}
        user_name = html.escape(from_user.get("first_name") or from_user.get("title") or "بەکارهێنەر")
        user_id   = from_user.get("id", chat_id)

        if from_user.get("id"):
            is_new_user = not await db_get(f"bot_users/{bid}/{user_id}")
            await db_patch(f"bot_users/{bid}/{user_id}", {"name": from_user.get("first_name",""), "chat_id": chat_id})
            # ئاگادارکردنەوەی خاوەنی بۆت کاتی بەکارهێنەری نوێ
            if is_new_user and txt.startswith("/start"):
                owner_uid = info.get("owner")
                notif_on  = info.get("notif_enabled", True)
                if owner_uid and notif_on:
                    R = "\u200f"
                    uname_str  = f"@{from_user.get('username')}" if from_user.get("username") else "—"
                    lang_code  = from_user.get("language_code", "—")
                    is_premium = "💎 بەڵێ" if from_user.get("is_premium") else "❌ نەخێر"
                    # ژمارەی کۆی بەکارهێنەران
                    total_bu = await db_get(f"bot_users/{bid}") or {}
                    notif_msg = (
                        f"{R}🔔 <b>بەکارهێنەری نوێی بۆتەکەت!</b>\n"
                        f"{R}━━━━━━━━━━━━━━━━━━━\n"
                        f"{R}👤 <b>ناو:</b> <a href='tg://user?id={user_id}'>{user_name}</a>\n"
                        f"{R}🆔 <b>ID:</b> <code>{user_id}</code>\n"
                        f"{R}🔗 <b>یوزەر:</b> {uname_str}\n"
                        f"{R}🌐 <b>زمان:</b> {lang_code}\n"
                        f"{R}💎 <b>پریمیوم:</b> {is_premium}\n"
                        f"{R}━━━━━━━━━━━━━━━━━━━\n"
                        f"{R}🤖 <b>بۆت:</b> @{bun}\n"
                        f"{R}👥 <b>کۆی بەکارهێنەران:</b> {len(total_bu)} کەس\n"
                        f"{R}⏰ <b>کات:</b> {now_str()}"
                    )
                    try:
                        await send_tg(MASTER_TOKEN, "sendMessage", {
                            "chat_id": owner_uid,
                            "text": notif_msg,
                            "parse_mode": "HTML"
                        })
                    except: pass

        async with httpx.AsyncClient(timeout=10) as c:
            bot_type = info.get("type", "reaction")

            # ════ بۆتی زانیاری ══════════════════════════════════════════════
            if bot_type == "info" and txt.startswith(("/id", "/info", "/start")):
                # پشکنینی جۆینی ناچاری
                if txt.startswith("/start") and fj and req_chs and from_user.get("id"):
                    not_joined = []
                    for ch in req_chs:
                        try:
                            res = await send_tg(token, "getChatMember", {"chat_id": f"@{ch}", "user_id": user_id})
                            status = res.get("result", {}).get("status", "left")
                            if status not in ("member","administrator","creator"):
                                not_joined.append(ch)
                        except:
                            not_joined.append(ch)
                    if not_joined:
                        kb_rows = [[{"text": f"📢 ئەندامبوون لە @{ch}", "url": f"https://t.me/{ch}"}] for ch in not_joined]
                        join_msg = "\u200f‼️ <b>تکایە سەرەتا ئەندامی کانالەکانمان بە:</b>\n\n"
                        for ch in not_joined:
                            join_msg += f"\u200f• @{ch}\n"
                        await c.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                            "chat_id": chat_id, "text": join_msg, "parse_mode": "HTML",
                            "reply_markup": {"inline_keyboard": kb_rows},
                        })
                        return

                if txt.startswith("/start"):
                    # بەخێرهاتنی بۆتی زانیاری
                    notice = await db_get("system/notice")
                    caption = wlcm.replace("{name}", user_name) if wlcm else (
                        f"\u200fسڵاو، <a href='tg://user?id={user_id}'>{user_name}</a> 👋\n\n"
                        f"\u200fمن بۆتی زانیاریم 🪪 ناوم <b>{html.escape(bnm)}</b>ە\n\n"
                        f"\u200fبۆ زانیاری خۆت بنووسە /id یان /info\n\n"
                        f"\u200fدەتوانم لە گروپ و کانالدا کار بکەم 🌼"
                    )
                    if notice:
                        caption += f"\n\n\u200f📌 <b>تێبینی:</b> {notice}"
                    keyboard = {"inline_keyboard": [
                        [{"text":"📢 کانالی بەڕێوەبەر","url":f"https://t.me/{sys_chan}"}],
                        [{"text":"➕ زیادکردن بۆ گروپ","url":f"https://t.me/{bun}?startgroup=new"},
                         {"text":"➕ زیادکردن بۆ کانال","url":f"https://t.me/{bun}?startchannel=new"}],
                        [{"text":"👨‍💻 بەرنامەنووس","url":f"tg://user?id={OWNER_ID}"}],
                    ]}
                    try:
                        await c.post(f"https://api.telegram.org/bot{token}/sendPhoto", json={
                            "chat_id":chat_id,"photo":sys_photo,"caption":caption,
                            "parse_mode":"HTML","reply_markup":keyboard,"reply_to_message_id":message_id,
                        })
                    except:
                        await c.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                            "chat_id":chat_id,"text":caption,
                            "parse_mode":"HTML","reply_markup":keyboard,"reply_to_message_id":message_id,
                        })
                    return

                # /id یان /info
                first_name = html.escape(from_user.get("first_name") or "—")
                uname_str  = f"@{from_user.get('username')}" if from_user.get("username") else "N/A"
                is_premium = "✅ بەڵێ" if from_user.get("is_premium") else "❌ نەخێر"
                lang_code  = from_user.get("language_code","—")

                # ستاتوسی کەس لە چات
                status_txt = "Member"
                try:
                    cm_res = await send_tg(token, "getChatMember", {"chat_id": chat_id, "user_id": user_id})
                    raw_st = cm_res.get("result",{}).get("status","member")
                    status_map = {
                        "creator":"👑 خاوەن","administrator":"🛡 ئەدمین",
                        "member":"👤 ئەندام","restricted":"🚫 سنووردار","left":"↩️ چووەتەوە"
                    }
                    status_txt = status_map.get(raw_st, raw_st.title())
                except: pass

                user_link = f"<a href='tg://user?id={user_id}'>🔗 پرۆفایل</a>"
                R = "\u200f"
                info_text = (
                    f"{R}.:•------------9🌟e------------•:.\n\n"
                    f"{R}      -ˏˋ <b>𝗨𝗦𝗘𝗥 𝗣𝗥𝗢𝗙𝗜𝗟𝗘</b> ˊˎ-\n\n"
                    f"{R}👤 ›› <b>ناو</b> ⵓ {first_name}\n"
                    f"{R}📧 ›› <b>یوزەر</b> ⵓ {uname_str}\n"
                    f"{R}🆔 ›› <b>ID</b> ⵓ <code>{user_id}</code>\n"
                    f"{R}✨ ›› <b>پریمیوم</b> ⵓ {is_premium}\n"
                    f"{R}🌐 ›› <b>زمان</b> ⵓ {lang_code}\n"
                    f"{R}🛡️ ›› <b>ڕۆڵ</b> ⵓ {status_txt}\n"
                    f"{R}🔗 ›› <b>لینک</b> ⵓ {user_link}\n\n"
                    f"{R}.:•------------9🌟e------------•:."
                )
                # ناردنی وێنەی پرۆفایل
                try:
                    ph_res = await send_tg(token, "getUserProfilePhotos", {"user_id": user_id, "limit": 1})
                    photos = ph_res.get("result", {}).get("photos", [])
                    if photos:
                        photo_id = photos[0][-1]["file_id"]
                        await c.post(f"https://api.telegram.org/bot{token}/sendPhoto", json={
                            "chat_id": chat_id, "photo": photo_id,
                            "caption": info_text, "parse_mode": "HTML",
                            "reply_to_message_id": message_id,
                        })
                    else:
                        raise Exception("no photo")
                except:
                    await c.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                        "chat_id": chat_id, "text": info_text, "parse_mode": "HTML",
                        "reply_to_message_id": message_id, "disable_web_page_preview": True,
                    })
                return

            # ════ بۆتی کەش و هەوا — /start ══════════════════════════════════
            if bot_type == "weather" and txt.startswith("/start"):
                if fj and req_chs and from_user.get("id"):
                    not_joined = []
                    for ch in req_chs:
                        try:
                            res = await send_tg(token, "getChatMember", {"chat_id": f"@{ch}", "user_id": user_id})
                            status = res.get("result", {}).get("status", "left")
                            if status not in ("member","administrator","creator"):
                                not_joined.append(ch)
                        except:
                            not_joined.append(ch)
                    if not_joined:
                        kb_rows = [[{"text": f"📢 ئەندامبوون لە @{ch}", "url": f"https://t.me/{ch}"}] for ch in not_joined]
                        join_msg = "\u200f‼️ <b>تکایە سەرەتا ئەندامی کانالەکانمان بە:</b>\n\n"
                        for ch in not_joined:
                            join_msg += f"\u200f• @{ch}\n"
                        await c.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                            "chat_id": chat_id, "text": join_msg, "parse_mode": "HTML",
                            "reply_markup": {"inline_keyboard": kb_rows},
                        })
                        return
                welcome_txt = wlcm.replace("{name}", user_name) if wlcm else WEATHER_WELCOME
                await c.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                    "chat_id": chat_id, "text": welcome_txt,
                    "parse_mode": "HTML", "reply_markup": weather_kb_main(),
                })
                return
# ════ بۆتی ڕیاکشن ═══════════════════════════════════════════════
            if bot_type == "reaction" and txt.startswith("/react"):
                # پشکنینی ئەدمین (تەنها ئەدمین و خاوەن دەتوانن بیگۆڕن)
                if msg["chat"]["type"] in ["group", "supergroup"]:
                    sender_id = from_user.get("id")
                    cm_res = await send_tg(token, "getChatMember", {"chat_id": chat_id, "user_id": sender_id})
                    status = cm_res.get("result", {}).get("status", "")
                    if status not in ["creator", "administrator"]:
                        return # نێرەر ئەدمین نییە بۆیە هیچ مەکە

                chat_settings = await db_get(f"bot_settings/{bid}/{chat_id}") or {"mode": "random", "emojis": []}
                keys = []
                row = []
                for e in EMOJIS[:24]:
                    mark = "✅" if chat_settings.get("mode") == "custom" and e in chat_settings.get("emojis", []) else ""
                    row.append({"text": f"{e}{mark}", "callback_data": f"react_tg_{e}"})
                    if len(row) == 4:
                        keys.append(row)
                        row = []
                rnd_mark = "✅" if chat_settings.get("mode") == "random" else ""
                keys.append([{"text": f"🎲 هەڕەمەکی (Random) {rnd_mark}", "callback_data": "react_rnd"}])
                keys.append([{"text": "✅ پاشەکەوتکردن و داخستن", "callback_data": "react_done"}])

                async with httpx.AsyncClient(timeout=10) as c:
                    await c.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                        "chat_id": chat_id, "text": "⚙️ <b>ڕێکخستنی ڕیاکشنەکانی ئەم چاتە:</b>\nئەو ئیمۆجییانە هەڵبژێرە کە دەتەوێت بۆتەکە بۆ پۆستەکانی دابنێت:",
                        "parse_mode": "HTML", "reply_markup": {"inline_keyboard": keys}
                    })
                    await c.post(f"https://api.telegram.org/bot{token}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
                return

            if txt.startswith("/start"):
                # پشکنینی جۆینی ناچاری کەناڵ
                if fj and req_chs and from_user.get("id"):
                    not_joined = []
                    for ch in req_chs:
                        try:
                            res = await send_tg(token, "getChatMember", {"chat_id": f"@{ch}", "user_id": user_id})
                            status = res.get("result", {}).get("status", "left")
                            if status not in ("member","administrator","creator"):
                                not_joined.append(ch)
                        except:
                            not_joined.append(ch)
                    if not_joined:
                        kb_rows = [[{"text": f"📢 ئەندامبوون لە @{ch}", "url": f"https://t.me/{ch}"}] for ch in not_joined]
                        join_msg = "‼️ <b>تکایە سەرەتا ئەندامی کانالەکانمان بە:</b>\n\n"
                        for ch in not_joined:
                            join_msg += f"• @{ch}\n"
                        await c.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": join_msg,
                            "parse_mode": "HTML",
                            "reply_markup": {"inline_keyboard": kb_rows},
                        })
                        return

                notice = await db_get("system/notice")

                if wlcm:
                    caption = wlcm.replace("{name}", user_name)
                else:
                    caption = (
                        f"سڵاو، <a href='tg://user?id={user_id}'>{user_name}</a> 👋\n\n"
                        f"من بۆتی ڕیاکشنم 🍓 ناوم <b>{html.escape(bnm)}</b>ە\n\n"
                        f"کارەکەم ئەوەیە کە بۆ هەموو نامەیەک ڕیاکشن بنێرم:\n"
                        f"{' '.join(EMOJIS)}\n\n"
                        "دەتوانم لە گروپ، کانال و چاتی تایبەتدا کار بکەم 🌼\n"
                        "تەنها زیادم بکە بۆ گروپ یان کانالەکەت و ئادمینم بکە ☘️\n"
                        "ئینجا بۆ هەموو نامەیەک ئیموجی دەنێرم 💗"
                    )
                if notice:
                    caption += f"\n\n📌 <b>تێبینی:</b> {notice}"

                keyboard = {"inline_keyboard": [
                    [{"text":"📢 کانالی بەڕێوەبەر","url":f"https://t.me/{sys_chan}"}],
                    [
                        {"text":"➕ زیادکردن بۆ گروپ", "url":f"https://t.me/{bun}?startgroup=new"},
                        {"text":"➕ زیادکردن بۆ کانال","url":f"https://t.me/{bun}?startchannel=new"},
                    ],
                    [{"text":"👨‍💻 بەرنامەنووس","url":f"tg://user?id={OWNER_ID}"}],
                ]}
                await c.post(f"https://api.telegram.org/bot{token}/sendPhoto", json={
                    "chat_id":chat_id,"photo":sys_photo,"caption":caption,
                    "parse_mode":"HTML","reply_markup":keyboard,"reply_to_message_id":message_id,
                })
            else:
                chat_settings = await db_get(f"bot_settings/{bid}/{chat_id}") or {"mode": "random", "emojis": []}
                if chat_settings.get("mode") == "custom" and chat_settings.get("emojis"):
                    emoji = random.choice(chat_settings["emojis"])
                else:
                    emoji = random.choice(EMOJIS)
                    
                await c.post(f"https://api.telegram.org/bot{token}/setMessageReaction", json={
                    "chat_id":chat_id,"message_id":message_id,
                    "reaction":[{"type":"emoji","emoji":emoji}],"is_big":False,
                })
    except Exception as e:
        logger.error(f"Child: {e}")



# ══════════════════════════════════════════════════════════════════════════════
# ██  یارمەتیدەری پانێل
# ══════════════════════════════════════════════════════════════════════════════
async def panel_stats_text(uid: int) -> str:
    all_u = await db_get("users") or {}
    all_v = await db_get("vip") or {}
    blk   = await db_get("blocked") or {}
    return T(uid, "panel_header",
        users=len(all_u), vip=len(all_v),
        blocked=len(blk), dl=CFG.get("total_dl", 0),
        uptime=uptime_str())

async def stats_text(uid: int) -> str:
    all_u = await db_get("users") or {}
    all_v = await db_get("vip") or {}
    blk   = await db_get("blocked") or {}
    return T(uid, "stats",
        users=len(all_u), vip=len(all_v),
        blocked=len(blk), dl=CFG.get("total_dl", 0),
        uptime=uptime_str())

def panel_unified_kb(uid: int) -> InlineKeyboardMarkup:
    lang = get_lang(uid)
    def L(ku, en, ar): return ku if lang=="ku" else (en if lang=="en" else ar)
    rows = [
        [IKB("📊 " + L("ئامارەکان","Statistics","الإحصائيات"), "adm_stats"),
         IKB("📢 " + L("برۆدکاست","Broadcast","إذاعة"), "adm_broadcast")],
        [IKB("🚫 " + L("بلۆک","Block User","حظر"), "adm_block"),
         IKB("👤 " + L("زانیاری بەکارهێنەر","User Info","معلومات"), "adm_userinfo")],
        [IKB("🛡 " + L("ئەدمینەکان","Manage Admins","المشرفون"), "adm_manage_admins")],
    ]
    if is_super(uid):
        maint_key = "maint_on" if CFG.get("maintenance") else "maint_off"
        rows += [
            [IKB("💎 VIP", "sup_vips"),
             IKB("📢 " + L("چەناڵەکان","Channels","القنوات"), "sup_channels")],
            [IKB(T(uid, maint_key), "sup_toggle_maint"),
             IKB("🔌 API", "sup_api_settings")],
            [IKB("🌍 " + L("زمانی بۆت","Bot Language","لغة البوت"), "sup_bot_lang")],
        ]
    if is_owner(uid):
        rows += [
            [IKB("🌌 " + L("سوپەر ئەدمین","Super Admins","السوبر مشرفين"), "own_super_adms"),
             IKB("✉️ " + L("بەخێرهاتن","Welcome Msg","رسالة الترحيب"), "own_welcome")],
            [IKB("🔄 " + L("ڕێسەتی ئامار","Reset Stats","إعادة الإحصائيات"), "own_reset_stats"),
             IKB("💾 " + L("باکئەپ","Backup","نسخ احتياطي"), "own_backup")],
        ]
    rows.append([IKB(T(uid,"btn_back"), "back_home")])
    return IKM(rows)

async def safe_answer(query, text="", alert=False):
    try: await query.answer(text, show_alert=alert)
    except: pass

async def safe_edit(query, text, kb=None, parse_mode="HTML"):
    try:
        if kb:
            await query.edit_message_text(text, parse_mode=parse_mode, reply_markup=kb)
        else:
            await query.edit_message_text(text, parse_mode=parse_mode)
    except Exception as e:
        logger.warning(f"safe_edit: {e}")

async def _build_start_content(uid: int):
    ud   = await db_get(f"users/{uid}") or {}
    name = html.escape(ud.get("name","بەکارهێنەر"))
    R    = "\u200f"
    if uid == OWNER_ID:
        all_b  = await db_get("managed_bots") or {}
        all_u  = await db_get("users") or {}
        run    = sum(1 for v in all_b.values() if v.get("status")=="running")
        adms   = await db_get("admins") or {}
        txt    = (
            f"{R}‼️ <b>بەخێربێیت خاوەنی سیستەم، {name}!</b>\n\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}👥 بەکارهێنەران: <b>{len(all_u)}</b>\n"
            f"{R}🤖 بۆتەکان: <b>{len(all_b)}</b>  (🟢{run}  🔴{len(all_b)-run})\n"
            f"{R}👨\u200d💼 ئەدمینەکان: <b>{len(adms)}</b>\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}👇 هەڵبژاردنێک بکە:"
        )
        return txt, kb_main(uid)
    elif is_admin_panel(uid):
        txt = (
            f"{R}‼️ <b>بەخێربێیت، ئەدمین {name}!</b>\n\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}🛡 دەستتە بۆ پانێلی کۆنترۆڵ\n"
            f"{R}🤖 دروستکردنی بۆتی تایبەتی خۆت\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}👇 هەڵبژاردنێک بکە:"
        )
        return txt, kb_main_admin(uid)
    else:
        vip_badge = " 💎" if await is_vip(uid) else ""
        vip_speed = "⚡ خێرا" if await is_vip(uid) else "🐢 ئاسایی"
        txt = (
            f"{R}‼️ <b>بەخێربێیت، {name}{vip_badge}!</b>\n\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}🤖 دروستکردنی بۆتی تایبەتی خۆت\n"
            f"{R}⚙️ کۆنترۆڵی تەواوی بۆتەکەت\n"
            f"{R}🚀 خێرایی: {vip_speed}\n"
            f"{R}━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{R}👇 هەڵبژاردنێک بکە:"
        )
        return txt, kb_main(uid)

async def show_bot_list_cq(query, uid: int):
    all_b = await db_get("managed_bots") or {}
    mine  = {k: v for k, v in all_b.items() if v.get("owner") == uid}
    if not mine:
        await safe_edit(query, "📭 <b>هیچ بۆتێکت دروست نەکردووە!</b>\n\nکلیک لە '➕ دروستکردنی بۆتی نوێ' بکە.", kb_main(uid))
        return
    rows = []
    for bid_k, info in mine.items():
        st    = "🟢" if info.get("status")=="running" else "🔴"
        btype = info.get("type","reaction")
        ticon = "🍓" if btype=="reaction" else ("🌤️" if btype=="weather" else "🪪")
        rows.append([IKB(f"{st} {ticon} @{info.get('bot_username','Bot')}", f"sel_bot_{bid_k}")])
    rows.append([IKB("🔙 گەڕانەوە بۆ سەرەتا", "back_home")])
    await safe_edit(query,
        f"📂 <b>بۆتەکانت ({len(mine)}):</b>\n🟢 کاردەکات  |  🔴 ڕاگیراوە\n🍓 ڕیاکشن  |  🪪 زانیاری  |  🌤️ کەش و هەوا",
        IKM(rows))

async def show_bot_control_cq(query, uid: int, bid: str, info: dict):
    R = "\u200f"
    st_icon  = "🟢" if info.get("status")=="running" else "🔴"
    st_txt   = "چالاک ✅" if info.get("status")=="running" else "ڕاگیراوە ❌"
    name     = html.escape(info.get("bot_name","ناسناو"))
    un       = info.get("bot_username","ناسناو")
    bu       = await db_get(f"bot_users/{bid}") or {}
    wlcm     = info.get("welcome_msg","")
    btype    = info.get("type","reaction")
    notif_on = info.get("notif_enabled",True)
    type_lbl = "🍓 بۆتی ڕیاکشن" if btype=="reaction" else ("🌤️ بۆتی کەش و هەوا" if btype=="weather" else "🪪 بۆتی زانیاری")
    msg = (
        f"{R}⚙️ <b>پانێلی کۆنترۆڵ</b>\n{R}━━━━━━━━━━━━━━━━━━━\n"
        f"{R}🤖 <b>ناو:</b> {name}\n{R}🔗 <b>یوزەر:</b> @{un}\n"
        f"{R}🆔 <b>ID:</b> <code>{bid}</code>\n{R}━━━━━━━━━━━━━━━━━━━\n"
        f"{R}{st_icon} <b>دۆخ:</b> {st_txt}\n{R}🎯 <b>جۆر:</b> {type_lbl}\n"
        f"{R}👥 <b>بەکارهێنەران:</b> <b>{len(bu)}</b> کەس\n"
        f"{R}✉️ <b>بەخێرهاتن:</b> {'✅ دانراوە' if wlcm else '❌ بەتاڵ'}\n"
        f"{R}🔔 <b>ئاگادارکردنەوە:</b> {'✅ چالاک' if notif_on else '❌ کوێژاو'}\n{R}━━━━━━━━━━━━━━━━━━━"
    )
    await safe_edit(query, msg, kb_control(uid))

async def handle_control_cq(query, uid: int, data: str):
    bid = await db_get(f"users/{uid}/selected_bot")
    if not bid:
        await safe_answer(query, "⚠️ تکایە سەرەتا بۆتێک هەڵبژێرە.", alert=True); return
    info = await db_get(f"managed_bots/{bid}")
    if not info:
        await db_del(f"users/{uid}/selected_bot")
        await safe_answer(query, "❌ بۆتەکە سڕاوەتەوە.", alert=True); return
    un    = info.get("bot_username","Bot")
    token = info.get("token","")
    if data == "ctl_start":
        info["status"] = "running"
        await db_put(f"managed_bots/{bid}", info)
        await safe_edit(query, f"✅ بۆتی @{un} دەستی پێکرد 🟢", kb_control(uid))
    elif data == "ctl_stop":
        info["status"] = "stopped"
        await db_put(f"managed_bots/{bid}", info)
        await safe_edit(query, f"🛑 بۆتی @{un} وەستاندرا 🔴", kb_control(uid))
    elif data == "ctl_restart":
        info["status"] = "running"
        await db_put(f"managed_bots/{bid}", info)
        await safe_edit(query, f"🔄 بۆتی @{un} نوێکرایەوە ✅", kb_control(uid))
    elif data == "ctl_info":
        await show_bot_control_cq(query, uid, bid, info)
    elif data == "ctl_welcome":
        await db_put(f"users/{uid}/state", f"edit_welcome:{bid}")
        cur = info.get("welcome_msg","")
        await safe_edit(query,
            f"✏️ <b>گۆڕینی نامەی بەخێرهاتن</b>\n\n📝 نامەی ئێستا:\n<code>{html.escape(cur) if cur else '(بەتاڵ)'}</code>\n\nنامەی نوێت بنووسە:\n💡 <code>{{name}}</code> بەکاربهێنە بۆ ناوی بەکارهێنەر",
            IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]]))
    elif data == "ctl_bc":
        bu = await db_get(f"bot_users/{bid}") or {}
        if not bu:
            await safe_answer(query, "📭 هیچ بەکارهێنەرێک بۆتەکەت بەکار نەهێناوە.", alert=True); return
        await db_put(f"users/{uid}/state", f"bot_bc:{bid}")
        await safe_edit(query,
            f"📨 <b>بڵاوکردنەوە بۆ بەکارهێنەرانی @{un}</b>\n\n👥 ژمارە: <b>{len(bu)}</b>\n\nپەیامەکەت بنووسە:",
            IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]]))
    elif data == "ctl_webhook" and uid == OWNER_ID:
        if token:
            safe_url = (PROJECT_URL or "").rstrip('/')
            r = await send_tg(token,"setWebhook",{"url":f"{safe_url}/api/bot/{token}","allowed_updates":["message","channel_post","callback_query"]})
            resp = "✅ وەبهووک نوێکرایەوە!" if r.get("ok") else f"❌ هەڵە: {r.get('description','')}"
            await safe_edit(query, resp, kb_control(uid))
        else:
            await safe_answer(query, "❌ تۆکێن نەدۆزرایەوە.", alert=True)
    elif data == "ctl_token" and uid == OWNER_ID:
        await db_put(f"users/{uid}/state", f"change_token:{bid}")
        await safe_edit(query, "🔑 تۆکێنی نوێ بنووسە:", IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]]))
    elif data == "ctl_del":
        await safe_edit(query,
            f"⚠️ <b>دڵنیایت؟</b>\n\nبۆتی @{un} بە تەواوی دەسڕیتەوە!",
            IKM([[IKB(f"✅ بەڵێ، @{un} بسڕەوە", f"confirm_del_yes_{bid}")],[IKB("❌ نەخێر", "cancel_state")]]))
    elif data in ("ctl_notif_on","ctl_notif_off"):
        info["notif_enabled"] = (data == "ctl_notif_on")
        await db_put(f"managed_bots/{bid}", info)
        lbl = "🔔 ئاگادارکردنەوە چالاک کرا" if data=="ctl_notif_on" else "🔕 ئاگادارکردنەوە کوژێنرایەوە"
        await safe_answer(query, lbl, alert=True)
        await show_bot_control_cq(query, uid, bid, info)

async def owner_list_bots_cq(query, filter_status=None):
    all_b = await db_get("managed_bots") or {}
    if filter_status:
        all_b = {k:v for k,v in all_b.items() if v.get("status")==filter_status}
    if not all_b:
        await safe_answer(query, "📭 هیچ بۆتێک نییە", alert=True); return
    lines = [f"🤖 <b>بۆتەکان ({len(all_b)}):</b>\n"]
    for bid, bd in list(all_b.items())[:40]:
        st  = "🟢" if bd.get("status")=="running" else "🔴"
        bu  = await db_get(f"bot_users/{bid}") or {}
        lines.append(f"{st} @{bd.get('bot_username','—')}  👥{len(bu)}  ID:<code>{bid}</code>")
    await safe_edit(query, "\n".join(lines), KB_BOTS())

async def owner_sys_info_cq(query):
    all_b = await db_get("managed_bots") or {}
    all_u = await db_get("users") or {}
    adms  = await db_get("admins") or {}
    run   = sum(1 for v in all_b.values() if v.get("status")=="running")
    purl  = await db_get("system/project_url") or PROJECT_URL or "نەدۆزرایەوە"
    fj    = await db_get("system/force_join") or False
    msg   = (
        f"⚙️ <b>زانیاری سیستەم</b>\n━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 PROJECT URL: <code>{purl}</code>\n"
        f"👥 بەکارهێنەران: <b>{len(all_u)}</b>\n"
        f"🤖 بۆتەکان: <b>{len(all_b)}</b>  (🟢{run})\n"
        f"👨‍💼 ئەدمینەکان: <b>{len(adms)}</b>\n"
        f"📢 جۆینی ناچاری: <b>{'چالاک' if fj else 'لەکارخراو'}</b>\n"
        f"⏰ کاتی ئێستا: <b>{now_str()}</b>"
    )
    await safe_edit(query, msg, KB_SYS())

async def owner_refresh_all_webhooks_cq(query):
    all_b = await db_get("managed_bots") or {}
    ok=fail=0
    safe_url = (PROJECT_URL or "").rstrip('/')
    for bid, bd in all_b.items():
        if bd.get("status")!="running": continue
        token = bd.get("token","")
        if not token: continue
        r = await send_tg(token,"setWebhook",{"url":f"{safe_url}/api/bot/{token}","allowed_updates":["message","channel_post","callback_query"]})
        if r.get("ok"): ok+=1
        else: fail+=1
        await asyncio.sleep(0.1)
    await safe_edit(query, f"✅ وەبهووک نوێکرایەوە!\n✅ سەرکەوتوو: {ok}  ❌ هەڵە: {fail}", KB_SYS())

# ══════════════════════════════════════════════════════════════════════════════
# ██  MASTER CALLBACK QUERY HANDLER
# ══════════════════════════════════════════════════════════════════════════════
async def master_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid   = query.from_user.id
    data  = query.data or ""
    await safe_answer(query)
    await load_sets_from_db()

    if data == "noop": return

    if data == "check_join":
        joined, not_joined = await check_force_join(uid)
        if joined:
            try: await query.delete_message()
            except: pass
            await master_start(update, ctx)
        else:
            await safe_answer(query, "هێشتا ئەندام نەبووی! / Not joined yet!", alert=True)
        return

    if data in ("back_home","cancel_state"):
        await db_del(f"users/{uid}/state")
        waiting_state.pop(uid, None)
        txt_msg, kb = await _build_start_content(uid)
        await safe_edit(query, txt_msg, kb)
        return

    # mk_* buttons
    if data == "mk_new":
        if uid != OWNER_ID and not is_admin_panel(uid):
            joined, not_joined = await check_force_join(uid)
            if not joined:
                lines = ["‼️ <b>تکایە سەرەتا ئەندامی کانالەکانمان بە:</b>\n"]
                kb_rows = []
                for ch in not_joined:
                    lines.append(f"📢 @{ch}")
                    kb_rows.append([IKU(f"➕ ئەندامبوون لە @{ch}", f"https://t.me/{ch}")])
                kb_rows.append([IKB("✅ پشکنینی ئەندامبوون", "check_join")])
                await safe_edit(query, "\n".join(lines), IKM(kb_rows))
                return
        await safe_edit(query, "\u200f🤖 <b>جۆری بۆتەکەت هەڵبژێرە</b>", KB_BOT_TYPE())
        return

    if data in ("bt_reaction","bt_info","bt_weather"):
        btype = data[3:]
        await db_put(f"users/{uid}/pending_bot_type", btype)
        await db_put(f"users/{uid}/state", "await_token")
        waiting_state[uid] = "await_token"
        icon = {"reaction":"🍓","info":"🪪","weather":"🌤️"}[btype]
        R = "\u200f"
        await safe_edit(query,
            f"{R}{icon} <b>تۆکێنی بۆتەکەت بنووسە</b>\n\n{R}📋 <b>مامەڵەکە:</b>\n{R}١. @BotFather\n{R}٢. /newbot\n{R}٣. تۆکێنەکە کۆپی بکە و بینێرە\n\n{R}⬇️ <b>تۆکێنەکەت لێرە بینێرە:</b>",
            IKM([[IKB("❌ هەڵوەشاندنەوە", "cancel_state")]]))
        return

    if data == "mk_list":
        await show_bot_list_cq(query, uid); return

    if data == "mk_stats":
        await safe_edit(query, await stats_text(uid), IKM([[IKB(T(uid,"btn_back"), "back_home")]])); return

    if data.startswith("sel_bot_"):
        bid = data[8:]
        all_b = await db_get("managed_bots") or {}
        info  = all_b.get(bid)
        if not info or info.get("owner") != uid:
            await safe_answer(query, "❌ بۆتەکە نەدۆزرایەوە", alert=True); return
        await db_put(f"users/{uid}/selected_bot", bid)
        await show_bot_control_cq(query, uid, bid, info); return

    if data.startswith("ctl_"):
        await handle_control_cq(query, uid, data); return

    if data.startswith("confirm_del_yes_"):
        bid = data[16:]
        info = await db_get(f"managed_bots/{bid}") or {}
        un   = info.get("bot_username","ناسناو")
        token = info.get("token","")
        if token:
            try: await send_tg(token,"deleteWebhook",{})
            except: pass
        await db_del(f"managed_bots/{bid}")
        await db_del(f"users/{uid}/selected_bot")
        await db_del(f"users/{uid}/state")
        await safe_edit(query, f"🗑 <b>بۆتی @{un} بە تەواوی سڕایەوە!</b>", kb_main(uid)); return

    # panel_unified
    if data == "panel_unified":
        if not is_admin_panel(uid):
            await safe_answer(query, "❌ دەستت پێ نییە", alert=True); return
        await safe_edit(query, await panel_stats_text(uid), panel_unified_kb(uid)); return

    # adm_stats
    if data == "adm_stats":
        if not is_admin_panel(uid): return
        await safe_edit(query, await stats_text(uid), IKM([[IKB(T(uid,"btn_refresh"),"adm_stats")],[IKB(T(uid,"btn_back"),"panel_unified")]])); return

    # adm_broadcast
    if data == "adm_broadcast":
        if not is_admin_panel(uid): return
        waiting_state[uid] = "broadcast_all"
        await db_put(f"users/{uid}/state", "broadcast_all")
        await safe_edit(query, T(uid,"bc_ask"), IKM([[IKB(T(uid,"btn_cancel"),"panel_unified")]])); return

    # adm_block
    if data == "adm_block":
        if not is_admin_panel(uid): return
        waiting_state[uid] = "action_blk_add"
        await db_put(f"users/{uid}/state","action_blk_add")
        await safe_edit(query, T(uid,"block_ask"), IKM([[IKB(T(uid,"btn_cancel"),"panel_unified")]])); return

    # adm_userinfo
    if data == "adm_userinfo":
        if not is_admin_panel(uid): return
        waiting_state[uid] = "action_info_check"
        await db_put(f"users/{uid}/state","action_info_check")
        await safe_edit(query, T(uid,"userinfo_ask"), IKM([[IKB(T(uid,"btn_cancel"),"panel_unified")]])); return

    # adm_manage_admins
    if data == "adm_manage_admins":
        if not is_admin_panel(uid): return
        adms = await db_get("admins") or {}
        txt_a = T(uid,"admins_title",count=len(adms))
        if adms:
            lines = [txt_a,""]
            for a_id, ad in list(adms.items())[:20]:
                nm = html.escape(ad.get("name","?") if isinstance(ad,dict) else "?")
                lines.append(f"• <a href='tg://user?id={a_id}'>{nm}</a> <code>{a_id}</code>")
            txt_a = "\n".join(lines)
        rows = [[IKB("➕","sup_add_adm")]]
        if is_super(uid): rows[0].append(IKB("➖","sup_rm_adm_list"))
        rows.append([IKB(T(uid,"btn_back"),"panel_unified")])
        await safe_edit(query, txt_a, IKM(rows)); return

    # sup_add_adm
    if data == "sup_add_adm":
        if not is_admin_panel(uid): return
        waiting_state[uid] = "action_adm_add"
        await db_put(f"users/{uid}/state","action_adm_add")
        await safe_edit(query, T(uid,"adm_add_ask"), IKM([[IKB(T(uid,"btn_cancel"),"adm_manage_admins")]])); return

    if data == "sup_rm_adm_list":
        if not is_super(uid): return
        adms = await db_get("admins") or {}
        if not adms:
            await safe_answer(query,"📭 هیچ ئەدمینێک نییە",alert=True); return
        rows = [[IKB(f"❌ {a_id}",f"sup_confirm_rm_adm_{a_id}")] for a_id in list(adms.keys())[:20]]
        rows.append([IKB(T(uid,"btn_back"),"adm_manage_admins")])
        await safe_edit(query, T(uid,"admins_title",count=len(adms)), IKM(rows)); return

    if data.startswith("sup_confirm_rm_adm_"):
        if not is_super(uid): return
        a_id = data[19:]
        await safe_edit(query, T(uid,"adm_rm_confirm",id=a_id), IKM([[IKB(T(uid,"btn_yes"),f"sup_do_rm_adm_{a_id}"),IKB(T(uid,"btn_no"),"sup_rm_adm_list")]])); return

    if data.startswith("sup_do_rm_adm_"):
        if not is_super(uid): return
        a_id = data[14:]
        await db_del(f"admins/{a_id}")
        admins_set.discard(int(a_id))
        await safe_edit(query, T(uid,"adm_rm_done",id=a_id), panel_unified_kb(uid)); return

    # sup_vips
    if data == "sup_vips":
        if not is_super(uid): return
        vips = await db_get("vip") or {}
        txt_v = T(uid,"vips_title",count=len(vips))
        if vips:
            lines = [txt_v,""]
            for v_id, vd in list(vips.items())[:20]:
                exp = vd.get("expires","?") if isinstance(vd,dict) else "?"
                lines.append(f"• <code>{v_id}</code> ⏰ {exp}")
            txt_v = "\n".join(lines)
        await safe_edit(query, txt_v, IKM([[IKB("➕","sup_add_vip"),IKB("➖","sup_rm_vip_list")],[IKB(T(uid,"btn_back"),"panel_unified")]])); return

    if data == "sup_add_vip":
        if not is_super(uid): return
        waiting_state[uid] = "action_vip_add"
        await db_put(f"users/{uid}/state","action_vip_add")
        await safe_edit(query, T(uid,"vip_add_ask"), IKM([[IKB(T(uid,"btn_cancel"),"sup_vips")]])); return

    if data == "sup_rm_vip_list":
        if not is_super(uid): return
        vips = await db_get("vip") or {}
        if not vips:
            await safe_answer(query,"📭 هیچ VIPێک نییە",alert=True); return
        rows = [[IKB(f"❌ {v_id}",f"sup_confirm_rm_vip_{v_id}")] for v_id in list(vips.keys())[:20]]
        rows.append([IKB(T(uid,"btn_back"),"sup_vips")])
        await safe_edit(query, T(uid,"vips_title",count=len(vips)), IKM(rows)); return

    if data.startswith("sup_confirm_rm_vip_"):
        if not is_super(uid): return
        v_id = data[19:]
        await safe_edit(query, f"⚠️ VIP {v_id}?", IKM([[IKB(T(uid,"btn_yes"),f"sup_do_rm_vip_{v_id}"),IKB(T(uid,"btn_no"),"sup_rm_vip_list")]])); return

    if data.startswith("sup_do_rm_vip_"):
        if not is_super(uid): return
        v_id = data[14:]
        await db_del(f"vip/{v_id}")
        vip_set.discard(int(v_id))
        await safe_edit(query, T(uid,"vip_rm_done",id=v_id), panel_unified_kb(uid)); return

    # sup_channels
    if data == "sup_channels":
        if not is_super(uid): return
        chs = await db_get("system/req_channels") or {}
        txt_c = T(uid,"ch_title",count=len(chs))
        if chs:
            lines = [txt_c,""]+[f"• @{c}" for c in chs.keys()]
            txt_c = "\n".join(lines)
        else:
            txt_c += "\n\n" + T(uid,"ch_empty")
        await safe_edit(query, txt_c, IKM([[IKB("➕","sup_add_ch"),IKB("➖","sup_rm_ch_list")],[IKB(T(uid,"btn_back"),"panel_unified")]])); return

    if data == "sup_add_ch":
        if not is_super(uid): return
        waiting_state[uid] = "action_add_ch"
        await db_put(f"users/{uid}/state","action_add_ch")
        await safe_edit(query, T(uid,"ch_add_ask"), IKM([[IKB(T(uid,"btn_cancel"),"sup_channels")]])); return

    if data == "sup_rm_ch_list":
        if not is_super(uid): return
        chs = await db_get("system/req_channels") or {}
        if not chs:
            await safe_answer(query, T(uid,"ch_empty"), alert=True); return
        rows = [[IKB(f"❌ @{c}",f"sup_confirm_rm_ch_{c}")] for c in chs.keys()]
        rows.append([IKB(T(uid,"btn_back"),"sup_channels")])
        await safe_edit(query, T(uid,"ch_rm_q"), IKM(rows)); return

    if data.startswith("sup_confirm_rm_ch_"):
        if not is_super(uid): return
        ch = data[18:]
        await safe_edit(query, T(uid,"ch_rm_confirm",ch=f"@{ch}"), IKM([[IKB(T(uid,"btn_yes"),f"sup_do_rm_ch_{ch}"),IKB(T(uid,"btn_no"),"sup_rm_ch_list")]])); return

    if data.startswith("sup_do_rm_ch_"):
        if not is_super(uid): return
        ch = data[13:]
        await db_del(f"system/req_channels/{ch}")
        if f"@{ch}" in channels_list: channels_list.remove(f"@{ch}")
        await safe_edit(query, T(uid,"ch_rm_done",ch=f"@{ch}"), panel_unified_kb(uid)); return

    # sup_toggle_maint
    if data == "sup_toggle_maint":
        if not is_super(uid): return
        CFG["maintenance"] = not CFG.get("maintenance", False)
        await db_put("sys/cfg", CFG)
        await safe_edit(query, await panel_stats_text(uid), panel_unified_kb(uid)); return

    # sup_api_settings
    if data == "sup_api_settings":
        if not is_super(uid): return
        act = CFG.get("active_api","auto")
        apis = {"auto":"🤖 Auto","tikwm":"TikWM","hyper":"Hyper API"}
        rows = [[IKB(("✅ " if act==k else "   ")+lbl, f"sup_setapi_{k}")] for k,lbl in apis.items()]
        rows.append([IKB(T(uid,"btn_back"),"panel_unified")])
        await safe_edit(query, T(uid,"api_title",act=act), IKM(rows)); return

    if data.startswith("sup_setapi_"):
        if not is_super(uid): return
        api_name = data[11:]
        if api_name in ("auto","tikwm","hyper"):
            CFG["active_api"] = api_name
            await db_put("sys/cfg", CFG)
        act = CFG.get("active_api","auto")
        apis = {"auto":"🤖 Auto","tikwm":"TikWM","hyper":"Hyper API"}
        rows = [[IKB(("✅ " if act==k else "   ")+lbl, f"sup_setapi_{k}")] for k,lbl in apis.items()]
        rows.append([IKB(T(uid,"btn_back"),"panel_unified")])
        await safe_edit(query, T(uid,"api_title",act=act), IKM(rows)); return

    # sup_bot_lang
    if data == "sup_bot_lang":
        if not is_super(uid): return
        cur = CFG.get("default_lang","ku")
        ln  = {"ku":"🔴🔆🟢 کوردی","en":"🇺🇸 English","ar":"🇸🇦 العربية"}
        await safe_edit(query, T(uid,"botlang_title",cur=ln.get(cur,cur)), IKM([[IKB(ln["ku"],"set_bot_lang_ku"),IKB(ln["en"],"set_bot_lang_en"),IKB(ln["ar"],"set_bot_lang_ar")],[IKB(T(uid,"btn_back"),"panel_unified")]])); return

    if data.startswith("set_bot_lang_"):
        if not is_super(uid): return
        lang = data[13:]
        if lang in ("ku","en","ar"):
            CFG["default_lang"] = lang
            await db_put("sys/cfg", CFG)
            ln = {"ku":"کوردی","en":"English","ar":"العربية"}
            await safe_answer(query, T(uid,"botlang_changed",lang=ln.get(lang,lang)), alert=True)
        await safe_edit(query, await panel_stats_text(uid), panel_unified_kb(uid)); return

    # own_super_adms
    if data == "own_super_adms":
        if not is_owner(uid): return
        sups = await db_get("sys/super_admins") or {}
        txt_s2 = T(uid,"sup_title",count=len(sups))
        if sups:
            lines = [txt_s2,""]
            for s_id, sd in list(sups.items())[:20]:
                nm = html.escape(sd.get("name","?") if isinstance(sd,dict) else "?")
                lines.append(f"• <a href='tg://user?id={s_id}'>{nm}</a> <code>{s_id}</code>")
            txt_s2 = "\n".join(lines)
        await safe_edit(query, txt_s2, IKM([[IKB("➕","own_add_sup"),IKB("➖","own_rm_sup_list")],[IKB(T(uid,"btn_back"),"panel_unified")]])); return

    if data == "own_add_sup":
        if not is_owner(uid): return
        waiting_state[uid] = "action_sup_add"
        await db_put(f"users/{uid}/state","action_sup_add")
        await safe_edit(query, T(uid,"sup_add_ask"), IKM([[IKB(T(uid,"btn_cancel"),"own_super_adms")]])); return

    if data == "own_rm_sup_list":
        if not is_owner(uid): return
        sups = await db_get("sys/super_admins") or {}
        if not sups:
            await safe_answer(query,"📭 هیچ سوپەر ئەدمینێک نییە",alert=True); return
        rows = [[IKB(f"❌ {s_id}",f"own_confirm_rm_sup_{s_id}")] for s_id in list(sups.keys())[:20]]
        rows.append([IKB(T(uid,"btn_back"),"own_super_adms")])
        await safe_edit(query, T(uid,"sup_title",count=len(sups)), IKM(rows)); return

    if data.startswith("own_confirm_rm_sup_"):
        if not is_owner(uid): return
        s_id = data[19:]
        await safe_edit(query, T(uid,"sup_rm_confirm",id=s_id), IKM([[IKB(T(uid,"btn_yes"),f"own_do_rm_sup_{s_id}"),IKB(T(uid,"btn_no"),"own_rm_sup_list")]])); return

    if data.startswith("own_do_rm_sup_"):
        if not is_owner(uid): return
        s_id = data[14:]
        await db_del(f"sys/super_admins/{s_id}")
        super_admins_set.discard(int(s_id))
        await safe_edit(query, T(uid,"sup_rm_done",id=s_id), panel_unified_kb(uid)); return

    # own_welcome
    if data == "own_welcome":
        if not is_owner(uid): return
        waiting_state[uid] = "set_welcome"
        await db_put(f"users/{uid}/state","set_welcome")
        await safe_edit(query, T(uid,"welcome_ask"), IKM([[IKB("🗑 پاككردن","own_clear_welcome")],[IKB(T(uid,"btn_back"),"panel_unified")]])); return

    if data == "own_clear_welcome":
        if not is_owner(uid): return
        CFG["welcome_msg"] = ""
        await db_put("sys/cfg", CFG)
        await safe_edit(query, await panel_stats_text(uid), panel_unified_kb(uid)); return

    # own_reset_stats
    if data == "own_reset_stats":
        if not is_owner(uid): return
        CFG["total_dl"] = 0; CFG["total_users"] = 0
        await db_put("sys/cfg", CFG)
        await safe_answer(query, T(uid,"stats_reset"), alert=True)
        await safe_edit(query, await panel_stats_text(uid), panel_unified_kb(uid)); return

    # own_backup
    if data == "own_backup":
        if not is_owner(uid): return
        await safe_answer(query, T(uid,"backup_prep"), alert=True)
        all_u = await db_get("users") or {}
        bd    = {"time":now_str(),"cfg":CFG,"users":{k:{"name":v.get("name",""),"username":v.get("username","")} for k,v in all_u.items()}}
        try:
            await ctx.bot.send_document(uid, document=json.dumps(bd,ensure_ascii=False,indent=2).encode(),
                filename=f"backup_{now_str().replace(' ','_').replace(':','-')}.json", caption="💾 Backup")
        except Exception as e:
            await ctx.bot.send_message(uid, f"❌ {e}")
        return

    # quick_* actions
    if data.startswith("quick_blk_"):
        if not is_owner(uid): return
        t_uid = int(data[10:])
        await db_put(f"blocked/{t_uid}", True); blocked_set.add(t_uid)
        await safe_answer(query, T(uid,"block_done",id=t_uid), alert=True); return

    if data.startswith("quick_vip_"):
        if not is_owner(uid): return
        t_uid = int(data[10:])
        await db_put(f"vip/{t_uid}", {"expires":"lifetime","added_by":uid,"date":now_str()}); vip_set.add(t_uid)
        await safe_answer(query, T(uid,"vip_add_done",id=t_uid), alert=True); return

    if data.startswith("quick_adm_"):
        if not is_owner(uid): return
        t_uid = int(data[10:])
        ud = await db_get(f"users/{t_uid}") or {}
        await db_put(f"admins/{t_uid}", {"added_by":uid,"date":now_str(),"name":ud.get("name","?")}); admins_set.add(t_uid)
        await safe_answer(query, T(uid,"adm_add_done",id=t_uid), alert=True); return

    if data.startswith("quick_inf_"):
        if not is_owner(uid): return
        t_uid = int(data[10:])
        ud = await db_get(f"users/{t_uid}") or {}
        vd = await db_get(f"vip/{t_uid}")
        msg_i = T(uid,"userinfo_result",name=html.escape(ud.get("name","?")),user=ud.get("username","?"),
            id=t_uid,vip="✅" if vd else "❌",lang=ud.get("lang","?"),dl=ud.get("dl",0),date=ud.get("date","?"))
        await ctx.bot.send_message(uid, msg_i, parse_mode="HTML"); return

    # own_* panel sections
    if data == "own_users":
        if not is_owner(uid): return
        await safe_edit(query, "👥 <b>بەشی بەکارهێنەران</b>\n\nهەڵبژاردنێک بکە:", KB_USERS()); return
    if data == "own_bots":
        if not is_owner(uid): return
        await safe_edit(query, "🤖 <b>بەشی بۆتەکان</b>\n\nهەڵبژاردنێک بکە:", KB_BOTS()); return
    if data == "own_msg":
        if not is_owner(uid): return
        await safe_edit(query, "📨 <b>بەشی پەیام</b>\n\nهەڵبژاردنێک بکە:", KB_MSG()); return
    if data == "own_sec":
        if not is_owner(uid): return
        await safe_edit(query, "🛡 <b>بەشی ئەمنیەت</b>\n\nهەڵبژاردنێک بکە:", KB_SEC()); return
    if data == "own_sys":
        if not is_owner(uid): return
        await safe_edit(query, "⚙️ <b>بەشی سیستەم</b>\n\nهەڵبژاردنێک بکە:", KB_SYS()); return
    if data == "own_notif":
        if not is_owner(uid): return
        await safe_edit(query, "🔔 <b>بەشی ئاگادارکردنەوە</b>\n\nهەڵبژاردنێک بکە:", KB_NOTIF_MAIN()); return

    if data == "own_chan":
        if not is_owner(uid): return
        fj = await db_get("system/force_join") or False
        req_chs = await db_get("system/req_channels") or {}
        await safe_edit(query, f"📢 <b>بەشی جۆینی ناچاری</b>\n\n📋 کانالە داواکراوەکان: <b>{len(req_chs)}</b>\n🔔 دۆخ: <b>{'✅ چالاک' if fj else '❌ لەکارخراو'}</b>\n\nهەڵبژاردنێک بکە:", KB_CHAN()); return

    if data == "own_child_fj":
        if not is_owner(uid): return
        all_b = await db_get("managed_bots") or {}
        chs   = await db_get("system/child_fj_channels") or {}
        fj_on = await db_get("system/child_fj_enabled") or False
        R = "\u200f"
        await safe_edit(query,
            f"{R}🌐 <b>جۆینی ناچاری بۆ بۆتی بەکارهێنەران</b>\n{R}━━━━━━━━━━━━━━━━━━━\n"
            f"{R}🤖 کۆی بۆتەکان: <b>{len(all_b)}</b>\n{R}📢 کانالەکان: <b>{len(chs)}</b>\n{R}{'✅ چالاک' if fj_on else '❌ لەکارخراو'}",
            KB_CHILD_FJ()); return

    # own_child_fj sub
    if data == "own_child_fj_add":
        if not is_owner(uid): return
        waiting_state[uid]="child_fj_add_ch"; await db_put(f"users/{uid}/state","child_fj_add_ch")
        await safe_edit(query,"📢 یوزەرنەیمی کانالەکە بنووسە (بەبێ @):",IKM([[IKB(T(uid,"btn_cancel"),"own_child_fj")]])); return
    if data == "own_child_fj_del":
        if not is_owner(uid): return
        waiting_state[uid]="child_fj_del_ch"; await db_put(f"users/{uid}/state","child_fj_del_ch")
        chs = await db_get("system/child_fj_channels") or {}
        lines = "\n".join([f"• @{c}" for c in chs.keys()]) or "📭 هیچ کانالێک نییە"
        await safe_edit(query,f"📋 کانالەکان:\n{lines}\n\nیوزەرنەیمی کانالەکە بنووسە (بەبێ @):",IKM([[IKB(T(uid,"btn_cancel"),"own_child_fj")]])); return
    if data == "own_child_fj_list":
        if not is_owner(uid): return
        chs = await db_get("system/child_fj_channels") or {}
        fj_on = await db_get("system/child_fj_enabled") or False
        R = "\u200f"
        lines = [f"{R}📋 <b>کانالەکانی جۆینی ناچاری:</b> ({'✅ چالاک' if fj_on else '❌ کوژاو'})\n"]+[f"• @{c}" for c in chs.keys()]
        await safe_edit(query,"\n".join(lines) if chs else "📭 هیچ کانالێک نییە",KB_CHILD_FJ()); return
    if data == "own_child_fj_on":
        if not is_owner(uid): return
        await db_put("system/child_fj_enabled",True); await safe_answer(query,"✅ چالاک کرا",alert=True); return
    if data == "own_child_fj_off":
        if not is_owner(uid): return
        await db_put("system/child_fj_enabled",False); await safe_answer(query,"🔕 کوژێنرایەوە",alert=True); return

    # own_notif sub
    if data == "own_notif_on":
        if not is_owner(uid): return
        all_b = await db_get("managed_bots") or {}
        for bid_k,binfo in {k:v for k,v in all_b.items() if v.get("owner")==uid}.items():
            binfo["notif_enabled"]=True; await db_put(f"managed_bots/{bid_k}",binfo)
        await safe_answer(query,"🔔 چالاک کرا",alert=True); return
    if data == "own_notif_off":
        if not is_owner(uid): return
        all_b = await db_get("managed_bots") or {}
        for bid_k,binfo in {k:v for k,v in all_b.items() if v.get("owner")==uid}.items():
            binfo["notif_enabled"]=False; await db_put(f"managed_bots/{bid_k}",binfo)
        await safe_answer(query,"🔕 کوژێنرایەوە",alert=True); return
    if data == "own_notif_bc":
        if not is_owner(uid): return
        waiting_state[uid]="notif_master"; await db_put(f"users/{uid}/state","notif_master")
        await safe_edit(query,"📢 نامەکەت بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"panel_unified")]])); return
    if data == "own_notif_users":
        if not is_owner(uid): return
        waiting_state[uid]="notif_all"; await db_put(f"users/{uid}/state","notif_all")
        await safe_edit(query,"📢 نامەکەت بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"panel_unified")]])); return
    if data == "own_notif_allbots":
        if not is_owner(uid): return
        waiting_state[uid]="notif_all_bots"; await db_put(f"users/{uid}/state","notif_all_bots")
        all_b = await db_get("managed_bots") or {}
        bot_uids: set = set()
        for bid_k in all_b:
            bu = await db_get(f"bot_users/{bid_k}") or {}; bot_uids.update(bu.keys())
        R = "\u200f"
        await safe_edit(query,f"{R}📡 <b>ناردنی نامە بۆ هەموو بۆتەکان</b>\n{R}👥 کۆی بەکارهێنەران: <b>{len(bot_uids)}</b>\n{R}🤖 ژمارەی بۆتەکان: <b>{len(all_b)}</b>\n\n{R}⬇️ نامەکەت بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"panel_unified")]])); return

    # own_fj sub
    if data == "own_fj_on":
        if not is_owner(uid): return
        await db_put("system/force_join",True); await safe_answer(query,"✅ چالاک کرا",alert=True); return
    if data == "own_fj_off":
        if not is_owner(uid): return
        await db_put("system/force_join",False); await safe_answer(query,"❌ لەکارخرا",alert=True); return
    if data == "own_fj_add":
        if not is_owner(uid): return
        waiting_state[uid]="add_req_channel"; await db_put(f"users/{uid}/state","add_req_channel")
        await safe_edit(query,"➕ یوزەرنەیمی کانالەکە بنووسە (بەبێ @):",IKM([[IKB(T(uid,"btn_cancel"),"own_chan")]])); return
    if data == "own_fj_del":
        if not is_owner(uid): return
        waiting_state[uid]="del_req_channel"; await db_put(f"users/{uid}/state","del_req_channel")
        await safe_edit(query,"➖ یوزەرنەیمی کانالەکە بنووسە (بەبێ @):",IKM([[IKB(T(uid,"btn_cancel"),"own_chan")]])); return
    if data == "own_fj_list":
        if not is_owner(uid): return
        main_ch = await db_get("system/channel") or CHANNEL_USER
        req_chs = await db_get("system/req_channels") or {}
        fj = await db_get("system/force_join") or False
        msg = f"📢 <b>کانالەکان</b>\n━━━━━━━━━━━━━━━━━━━\n📢 کانالی سەرەکی: @{main_ch}\n🔔 دۆخ: <b>{'✅ چالاک' if fj else '❌ لەکارخراو'}</b>\n\n📋 <b>کانالە داواکراوەکان ({len(req_chs)}):</b>\n"
        for i, ch in enumerate(req_chs, 1):
            msg += f"  {i}. 🔗 @{ch}\n"
        await safe_edit(query, msg if req_chs else msg+"  📭 هیچ کانالێک نییە\n", KB_CHAN()); return
    if data == "own_fj_check":
        if not is_owner(uid): return
        waiting_state[uid]="check_member"; await db_put(f"users/{uid}/state","check_member")
        await safe_edit(query,"🆔 ID ی بەکارهێنەر بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"own_chan")]])); return
    if data == "own_fj_stats":
        if not is_owner(uid): return
        req_chs = await db_get("system/req_channels") or {}
        fj = await db_get("system/force_join") or False
        all_u = await db_get("users") or {}
        msg = (f"📊 <b>ئامارەکانی جۆینی ناچاری</b>\n━━━━━━━━━━━━━━━━━━━\n"
               f"🔔 دۆخ: <b>{'✅ چالاک' if fj else '❌ لەکارخراو'}</b>\n"
               f"📋 کانالە داواکراوەکان: <b>{len(req_chs)}</b>\n👥 کۆی بەکارهێنەران: <b>{len(all_u)}</b>")
        await safe_edit(query, msg, KB_CHAN()); return
    if data == "own_fj_clear":
        if not is_owner(uid): return
        await db_del("system/req_channels"); channels_list.clear()
        await safe_answer(query,"🗑 هەموو کانالە داواکراوەکان سڕایەوە",alert=True); return
    if data == "own_chan_main":
        if not is_owner(uid): return
        waiting_state[uid]="change_main_channel"; await db_put(f"users/{uid}/state","change_main_channel")
        await safe_edit(query,"📢 یوزەرنەیمی کانالی نوێ بنووسە (بەبێ @):",IKM([[IKB(T(uid,"btn_cancel"),"own_chan")]])); return

    # own_sys sub
    if data == "own_sys_info":
        if not is_owner(uid): return
        await owner_sys_info_cq(query); return
    if data == "own_sys_wh":
        if not is_owner(uid): return
        await owner_refresh_all_webhooks_cq(query); return
    if data == "own_sys_clear":
        if not is_owner(uid): return
        await safe_edit(query,"⚠️ <b>دڵنیایت؟</b> هەموو داتاکان دەسڕیتەوە!",IKM([[IKB("✅ بەڵێ، پاک بکەرەوە","own_sys_clear_yes"),IKB(T(uid,"btn_cancel"),"own_sys")]])); return
    if data == "own_sys_clear_yes":
        if not is_owner(uid): return
        await db_del("users"); await db_del("managed_bots"); await db_del("bot_users")
        await safe_edit(query,"✅ داتابەیس پاک کرایەوە.",KB_SYS()); return
    if data == "own_sys_token":
        if not is_owner(uid): return
        waiting_state[uid]="change_master_token"; await db_put(f"users/{uid}/state","change_master_token")
        await safe_edit(query,"🔑 تۆکێنی نوێی بۆتی سەرەکی بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"own_sys")]])); return
    if data == "own_sys_url":
        if not is_owner(uid): return
        waiting_state[uid]="change_project_url"; await db_put(f"users/{uid}/state","change_project_url")
        cur = await db_get("system/project_url") or PROJECT_URL or "نییە"
        await safe_edit(query,f"🌐 URL ی ئێستا: <code>{cur}</code>\n\nURL ی نوێ بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"own_sys")]])); return
    if data == "own_sys_logs":
        if not is_owner(uid): return
        logs = await db_get("system/logs") or []
        if isinstance(logs,dict): logs=list(logs.values())
        if not logs:
            await safe_answer(query,"📭 هیچ لۆگێک نییە",alert=True); return
        lines = ["📋 <b>دوایین لۆگەکان:</b>\n"]+[f"• {l}" for l in logs[:15]]
        await safe_edit(query,"\n".join(lines),KB_SYS()); return
    if data == "own_sys_restart":
        if not is_owner(uid): return
        await safe_edit(query,"⚠️ دڵنیایت لە ڕیستارتکردنی سیستەم؟",IKM([[IKB("✅ بەڵێ","own_sys_restart_yes"),IKB(T(uid,"btn_cancel"),"own_sys")]])); return
    if data == "own_sys_restart_yes":
        if not is_owner(uid): return
        await safe_edit(query,"🔃 ڕیستارت ئەنجامدرا...\n\n⚠️ تێبینی: ڕیستارتی ڕاستەقینە پێویستی بە Vercel CLI ئەکات.",KB_SYS()); return
    if data == "own_sys_dev_ch":
        if not is_owner(uid): return
        waiting_state[uid]="change_dev_channel"; await db_put(f"users/{uid}/state","change_dev_channel")
        await safe_edit(query,"📢 یوزەرنەیمی کانالی بەڕێوەبەری نوێ بنووسە (بەبێ @):",IKM([[IKB(T(uid,"btn_cancel"),"own_sys")]])); return
    if data == "own_sys_photo":
        if not is_owner(uid): return
        waiting_state[uid]="change_photo_url"; await db_put(f"users/{uid}/state","change_photo_url")
        await safe_edit(query,"🖼 لینکی وێنەی نوێ بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"own_sys")]])); return

    # own_user sub
    if data == "own_user_list":
        if not is_owner(uid): return
        all_u = await db_get("users") or {}
        if not all_u:
            await safe_answer(query,"📭 هیچ بەکارهێنەرێک نییە",alert=True); return
        lines = [f"👥 <b>لیستی بەکارهێنەران ({len(all_u)}):</b>\n"]
        for u_id,ud in list(all_u.items())[:50]:
            n=html.escape(ud.get("name","ناسناو")); un=f"@{ud['username']}" if ud.get("username") else "—"
            lines.append(f"• <a href='tg://user?id={u_id}'>{n}</a> {un} <code>{u_id}</code>")
        if len(all_u)>50: lines.append(f"\n... و {len(all_u)-50} تری دیکە")
        await safe_edit(query,"\n".join(lines),KB_USERS()); return
    if data == "own_user_search":
        if not is_owner(uid): return
        waiting_state[uid]="search_user"; await db_put(f"users/{uid}/state","search_user")
        await safe_edit(query,"🔍 ناو یان یوزەرنەیم یان ID بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"own_users")]])); return
    if data == "own_user_stats":
        if not is_owner(uid): return
        all_u=await db_get("users") or {}; all_v=await db_get("vip") or {}
        all_bl=await db_get("blocked") or {}; all_w=await db_get("warnings") or {}; adms=await db_get("admins") or {}
        vip_ids=set(all_v.keys())
        msg = (f"📊 <b>ئامارەکانی بەکارهێنەران</b>\n━━━━━━━━━━━━━━━━━━━\n"
               f"👥 کۆی بەکارهێنەران: <b>{len(all_u)}</b>\n💎 VIPەکان: <b>{len(all_v)}</b>\n"
               f"👨‍💼 ئەدمینەکان: <b>{len(adms)}</b>\n🚫 بلۆکەکان: <b>{len(all_bl)}</b>\n"
               f"⚠️ ئاگادارکراوەکان: <b>{len(all_w)}</b>\n"
               f"👤 نا-VIP: <b>{len(all_u)-len([i for i in all_u if i in vip_ids])}</b>")
        await safe_edit(query,msg,KB_USERS()); return
    if data == "own_user_del":
        if not is_owner(uid): return
        waiting_state[uid]="del_user"; await db_put(f"users/{uid}/state","del_user")
        await safe_edit(query,"🆔 ID ی بەکارهێنەرەکە بنووسە تا بیسڕیتەوە:",IKM([[IKB(T(uid,"btn_cancel"),"own_users")]])); return
    if data == "own_user_export":
        if not is_owner(uid): return
        all_u=await db_get("users") or {}
        lines=["ID | ناو | یوزەر | کاتی دوایین چالاکی"]
        for u_id,ud in all_u.items():
            lines.append(f"{u_id} | {ud.get('name','')} | @{ud.get('username','')} | {ud.get('last_seen','')}")
        txt_exp="\n".join(lines)
        await safe_edit(query,f"📤 <b>لیستی بەکارهێنەران ({len(all_u)}):</b>\n\n<code>{html.escape(txt_exp[:3500])}</code>",KB_USERS()); return

    # own_bot sub
    if data == "own_bot_list":
        if not is_owner(uid): return
        await owner_list_bots_cq(query,filter_status=None); return
    if data == "own_bot_running":
        if not is_owner(uid): return
        await owner_list_bots_cq(query,filter_status="running"); return
    if data == "own_bot_stopped":
        if not is_owner(uid): return
        await owner_list_bots_cq(query,filter_status="stopped"); return
    if data == "own_bot_stats":
        if not is_owner(uid): return
        all_b=await db_get("managed_bots") or {}
        run=sum(1 for v in all_b.values() if v.get("status")=="running")
        total_bu=0
        for bid_k in all_b:
            bu=await db_get(f"bot_users/{bid_k}") or {}; total_bu+=len(bu)
        msg=(f"📊 <b>ئامارەکانی بۆتەکان</b>\n━━━━━━━━━━━━━━━━━━━\n"
             f"🤖 کۆی بۆتەکان: <b>{len(all_b)}</b>\n🟢 چالاک: <b>{run}</b>\n"
             f"🔴 ڕاگیراو: <b>{len(all_b)-run}</b>\n👥 کۆی بەکارهێنەران: <b>{total_bu}</b>")
        await safe_edit(query,msg,KB_BOTS()); return
    if data == "own_bot_all_start":
        if not is_owner(uid): return
        all_b=await db_get("managed_bots") or {}
        for bid_k,bd in all_b.items():
            bd["status"]="running"; await db_put(f"managed_bots/{bid_k}",bd)
        await safe_answer(query,f"🟢 هەموو {len(all_b)} بۆت دەستی پێکرد",alert=True); return
    if data == "own_bot_all_stop":
        if not is_owner(uid): return
        all_b=await db_get("managed_bots") or {}
        for bid_k,bd in all_b.items():
            bd["status"]="stopped"; await db_put(f"managed_bots/{bid_k}",bd)
        await safe_answer(query,f"🔴 هەموو {len(all_b)} بۆت وەستاندرا",alert=True); return
    if data == "own_bot_del_id":
        if not is_owner(uid): return
        waiting_state[uid]="owner_del_bot"; await db_put(f"users/{uid}/state","owner_del_bot")
        await safe_edit(query,"🆔 ID ی بۆتەکە بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"own_bots")]])); return
    if data == "own_bot_search":
        if not is_owner(uid): return
        waiting_state[uid]="search_bot"; await db_put(f"users/{uid}/state","search_bot")
        await safe_edit(query,"🔍 یوزەرنەیم یان ID ی بۆتەکە بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"own_bots")]])); return

    # own_msg sub
    if data in ("own_bc_all","own_bc_vip","own_bc_nonvip"):
        if not is_owner(uid): return
        sm={"own_bc_all":"bc_all","own_bc_vip":"bc_vip","own_bc_nonvip":"bc_nonvip"}[data]
        waiting_state[uid]=sm; await db_put(f"users/{uid}/state",sm)
        await safe_edit(query,"📨 پەیامەکەت بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"own_msg")]])); return
    if data == "own_msg_one":
        if not is_owner(uid): return
        waiting_state[uid]="msg_one_id"; await db_put(f"users/{uid}/state","msg_one_id")
        await safe_edit(query,"🆔 ID ی بەکارهێنەرەکە بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"own_msg")]])); return
    if data == "own_bc_allbots":
        if not is_owner(uid): return
        all_b=await db_get("managed_bots") or {}
        total_u: set=set()
        for bid_k in all_b:
            bu=await db_get(f"bot_users/{bid_k}") or {}; total_u.update(bu.keys())
        waiting_state[uid]="bc_all_child_bots"; await db_put(f"users/{uid}/state","bc_all_child_bots")
        R="\u200f"
        await safe_edit(query,f"{R}📡 <b>ناردن بۆ هەموو بۆتەکان</b>\n{R}🤖 بۆتەکان: <b>{len(all_b)}</b>\n{R}👥 بەکارهێنەران: <b>{len(total_u)}</b>\n\n{R}⬇️ پەیامەکەت بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"own_msg")]])); return
    if data == "own_sys_msg_set":
        if not is_owner(uid): return
        waiting_state[uid]="set_sys_msg"; await db_put(f"users/{uid}/state","set_sys_msg")
        await safe_edit(query,"📌 پەیامی سیستەم بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"own_msg")]])); return
    if data == "own_sys_msg_del":
        if not is_owner(uid): return
        await db_del("system/notice"); await safe_answer(query,"✅ پەیامی سیستەم سڕایەوە",alert=True); return
    if data == "own_sys_msg_view":
        if not is_owner(uid): return
        msg_now=await db_get("system/notice")
        if msg_now:
            await safe_edit(query,f"📌 <b>پەیامی سیستەمی ئێستا:</b>\n\n{msg_now}",KB_MSG())
        else:
            await safe_answer(query,"📭 هیچ پەیامی سیستەمێک دانەنراوە",alert=True); return
    if data == "own_bc_hist":
        if not is_owner(uid): return
        hist=await db_get("system/bc_history") or []
        if isinstance(hist,dict): hist=list(hist.values())
        if not hist:
            await safe_answer(query,"📭 هیچ مێژووی بڵاوکردنەوە نییە",alert=True); return
        lines=["📜 <b>مێژووی بڵاوکردنەوە:</b>\n"]+[f"📤 {h.get('time','—')} | {h.get('type','—')} | ✅{h.get('sent',0)} ❌{h.get('fail',0)}" for h in hist[:15]]
        await safe_edit(query,"\n".join(lines),KB_MSG()); return

    # own_vip sub
    if data == "own_vip_stats":
        if not is_owner(uid): return
        all_v=await db_get("vip") or {}
        life=sum(1 for v in all_v.values() if isinstance(v,dict) and v.get("expires")=="lifetime")
        msg=(f"📊 <b>ئامارەکانی VIP</b>\n━━━━━━━━━━━━━━━━\n💎 کۆی VIPەکان: <b>{len(all_v)}</b>\n♾ هەمیشەیی: <b>{life}</b>\n⏰ کاتی دیاریکراو: <b>{len(all_v)-life}</b>")
        await safe_edit(query,msg,KB_VIP()); return
    if data == "own_vip_date":
        if not is_owner(uid): return
        waiting_state[uid]="add_vip_date"; await db_put(f"users/{uid}/state","add_vip_date")
        await safe_edit(query,"🆔 ID و بەرواری بەسەرچوون بنووسە:\nنموونە: <code>123456789 2025-12-31</code>",IKM([[IKB(T(uid,"btn_cancel"),"sup_vips")]])); return
    if data == "own_vip_life":
        if not is_owner(uid): return
        waiting_state[uid]="add_vip_life"; await db_put(f"users/{uid}/state","add_vip_life")
        await safe_edit(query,"🆔 ID ی بەکارهێنەر بنووسە (VIP بۆ هەمیشە):",IKM([[IKB(T(uid,"btn_cancel"),"sup_vips")]])); return
    if data == "own_vip_check":
        if not is_owner(uid): return
        waiting_state[uid]="check_vip"; await db_put(f"users/{uid}/state","check_vip")
        await safe_edit(query,"🆔 ID ی بەکارهێنەر بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"sup_vips")]])); return
    if data == "own_vip_del_all":
        if not is_owner(uid): return
        await safe_edit(query,"⚠️ <b>دڵنیایت؟</b> هەموو VIPەکان دەسڕیتەوە!",IKM([[IKB("✅ بەڵێ، هەموو VIP بسڕەوە","own_vip_del_all_yes"),IKB(T(uid,"btn_cancel"),"sup_vips")]])); return
    if data == "own_vip_del_all_yes":
        if not is_owner(uid): return
        await db_del("vip"); vip_set.clear()
        await safe_edit(query,"✅ هەموو VIPەکان سڕایەوە.",KB_VIP()); return

    # own_sec sub
    if data == "own_unblock":
        if not is_owner(uid): return
        waiting_state[uid]="unblock_user"; await db_put(f"users/{uid}/state","unblock_user")
        await safe_edit(query,"🆔 ID ی بەکارهێنەرەکە بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"own_sec")]])); return
    if data == "own_blocklist":
        if not is_owner(uid): return
        all_bl=await db_get("blocked") or {}
        if not all_bl:
            await safe_answer(query,"📭 هیچ بلۆکێک نییە",alert=True); return
        lines=[f"🚫 <b>بلۆکەکان ({len(all_bl)}):</b>\n"]+[f"• <code>{bid}</code>" for bid in list(all_bl.keys())[:40]]
        await safe_edit(query,"\n".join(lines),KB_SEC()); return
    if data == "own_block_clear":
        if not is_owner(uid): return
        await db_del("blocked"); blocked_set.clear()
        await safe_answer(query,"✅ هەموو بلۆکەکان سڕایەوە",alert=True); return
    if data == "own_warn":
        if not is_owner(uid): return
        waiting_state[uid]="warn_user_id"; await db_put(f"users/{uid}/state","warn_user_id")
        await safe_edit(query,"🆔 ID ی بەکارهێنەر بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"own_sec")]])); return
    if data == "own_restrict":
        if not is_owner(uid): return
        waiting_state[uid]="restrict_feat"; await db_put(f"users/{uid}/state","restrict_feat")
        await safe_edit(query,"🔒 ناوی فیچەر بنووسە:",IKM([[IKB(T(uid,"btn_cancel"),"own_sec")]])); return
    if data == "own_alert_mode":
        if not is_owner(uid): return
        cur=await db_get("system/alert_mode") or False
        await db_put("system/alert_mode",not cur)
        await safe_answer(query,f"🛡 مۆدی ئاگادارکردنەوە: {'چالاک ✅' if not cur else 'لەکارخراو ❌'}",alert=True); return
    if data == "own_warned_list":
        if not is_owner(uid): return
        all_w=await db_get("warnings") or {}
        if not all_w:
            await safe_answer(query,"📭 هیچ ئاگادارکراوێک نییە",alert=True); return
        lines=[f"⚠️ <b>ئاگادارکراوەکان ({len(all_w)}):</b>\n"]+[f"• <code>{w_id}</code> — ⚠️ {cnt} جار" for w_id,cnt in list(all_w.items())[:40]]
        await safe_edit(query,"\n".join(lines),KB_SEC()); return
    if data == "own_adm_stats":
        if not is_owner(uid): return
        adms=await db_get("admins") or {}
        msg=(f"📊 <b>ئامارەکانی ئەدمینەکان</b>\n━━━━━━━━━━━━━━━━━━━\n👨‍💼 کۆی ئەدمینەکان: <b>{len(adms)}</b>\n👑 خاوەنی سیستەم: <b>1</b>")
        await safe_edit(query,msg,KB_ADMINS()); return


# ══════════════════════════════════════════════════════════════════════════════
# ██  handle_text_new — تەنها بۆ states (نووسینی ژمارە/متن)
# ══════════════════════════════════════════════════════════════════════════════
async def handle_text_new(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt  = update.message.text.strip() if update.message and update.message.text else ""
    uid  = update.effective_user.id
    await load_sets_from_db()

    if uid in blocked_set or await is_blocked(uid):
        await update.message.reply_text("🚫 دەستت لە بۆتەکە گرتراوە."); return

    state = waiting_state.get(uid) or await db_get(f"users/{uid}/state") or ""

    if CFG.get("maintenance") and not is_admin_panel(uid):
        dev = f"@{CHANNEL_USER}"
        await update.message.reply_text(T(uid,"maint_msg",dev=dev), parse_mode="HTML"); return

    if state in ("await_token","await_token_react"):
        if re.match(r"^\d{8,10}:[A-Za-z0-9_-]{35}$", txt):
            await activate_token(update, uid, txt)
        else:
            await update.message.reply_text("⚠️ تۆکێنەکە دروست نییە.\nنموونە: <code>123456789:ABCxyz...</code>", parse_mode="HTML")
        return

    if state == "set_welcome":
        CFG["welcome_msg"] = txt
        await db_put("sys/cfg", CFG)
        waiting_state.pop(uid, None); await db_del(f"users/{uid}/state")
        await update.message.reply_text(T(uid,"welcome_saved"), parse_mode="HTML", reply_markup=kb_main(uid)); return

    if state == "broadcast_all":
        all_u = await db_get("users") or {}
        sm = await update.message.reply_text(T(uid,"bc_progress",done=0,total=len(all_u)))
        ok=fail=0
        for i,u_id in enumerate(all_u.keys()):
            try: await update.message.copy_to(int(u_id)); ok+=1
            except: fail+=1
            if (i+1)%20==0:
                try: await sm.edit_text(T(uid,"bc_progress",done=i+1,total=len(all_u)))
                except: pass
            await asyncio.sleep(0.05)
        waiting_state.pop(uid,None); await db_del(f"users/{uid}/state")
        await sm.edit_text(T(uid,"bc_done",ok=ok,fail=fail)); return

    if state == "action_blk_add":
        try:
            t_id=int(txt.strip()); await db_put(f"blocked/{t_id}",True); blocked_set.add(t_id)
            waiting_state.pop(uid,None); await db_del(f"users/{uid}/state")
            await update.message.reply_text(T(uid,"block_done",id=t_id), parse_mode="HTML", reply_markup=kb_main(uid))
        except: await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    if state == "action_info_check":
        try:
            t_id=int(txt.strip()); ud=await db_get(f"users/{t_id}") or {}; vd=await db_get(f"vip/{t_id}")
            waiting_state.pop(uid,None); await db_del(f"users/{uid}/state")
            msg_i=T(uid,"userinfo_result",name=html.escape(ud.get("name","?")),user=ud.get("username","?"),
                id=t_id,vip="✅" if vd else "❌",lang=ud.get("lang","?"),dl=ud.get("dl",0),date=ud.get("date","?"))
            await update.message.reply_text(msg_i, parse_mode="HTML", reply_markup=kb_main(uid))
        except: await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    if state == "action_adm_add":
        try:
            t_id=int(txt.strip()); ud=await db_get(f"users/{t_id}") or {}
            await db_put(f"admins/{t_id}",{"added_by":uid,"date":now_str(),"name":ud.get("name","?")}); admins_set.add(t_id)
            try: await send_tg(MASTER_TOKEN,"sendMessage",{"chat_id":t_id,"text":"‼️ <b>پیرۆزبێت!</b> 🎉\n\nتۆ بوویت بە ئەدمینی بۆتی سیستەم.\n🛡 ئێستا دەستتە بۆ پانێلی کۆنترۆڵ.","parse_mode":"HTML"})
            except: pass
            waiting_state.pop(uid,None); await db_del(f"users/{uid}/state")
            await update.message.reply_text(T(uid,"adm_add_done",id=t_id), parse_mode="HTML", reply_markup=kb_main(uid))
        except: await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    if state == "action_vip_add":
        try:
            t_id=int(txt.strip()); await db_put(f"vip/{t_id}",{"expires":"lifetime","added_by":uid,"date":now_str()}); vip_set.add(t_id)
            waiting_state.pop(uid,None); await db_del(f"users/{uid}/state")
            await update.message.reply_text(T(uid,"vip_add_done",id=t_id), parse_mode="HTML", reply_markup=kb_main(uid))
        except: await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    if state == "action_add_ch":
        ch = txt.strip()
        if not ch.startswith("@") or len(ch)<3:
            await update.message.reply_text(T(uid,"ch_add_err"), parse_mode="HTML"); return
        ch_name=ch.lstrip("@"); await db_put(f"system/req_channels/{ch_name}",True)
        if ch not in channels_list: channels_list.append(ch)
        waiting_state.pop(uid,None); await db_del(f"users/{uid}/state")
        await update.message.reply_text(T(uid,"ch_add_done",ch=ch), parse_mode="HTML", reply_markup=kb_main(uid)); return

    if state == "action_sup_add":
        try:
            t_id=int(txt.strip()); ud=await db_get(f"users/{t_id}") or {}
            await db_put(f"sys/super_admins/{t_id}",{"added_by":uid,"date":now_str(),"name":ud.get("name","?")})
            await db_put(f"admins/{t_id}",{"added_by":uid,"date":now_str(),"name":ud.get("name","?")})
            super_admins_set.add(t_id); admins_set.add(t_id)
            waiting_state.pop(uid,None); await db_del(f"users/{uid}/state")
            await update.message.reply_text(T(uid,"sup_add_done",id=t_id), parse_mode="HTML", reply_markup=kb_main(uid))
        except: await update.message.reply_text("⚠️ ID ی دروست بنووسە.")
        return

    # هەموو states ی کۆنی handle_states
    await handle_states(update, uid, txt, state)


# ══════════════════════════════════════════════════════════════════════════════
# ── ڕاوتەرەکان
# ══════════════════════════════════════════════════════════════════════════════
master_app = ApplicationBuilder().token(MASTER_TOKEN).build()
master_app.add_handler(CommandHandler("start", master_start))
master_app.add_handler(CallbackQueryHandler(master_callback))
master_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_text_new))


@app.post("/api/main")
async def master_route(request: Request):
    if not master_app.running:
        await master_app.initialize()
    data = await request.json()
    await master_app.process_update(Update.de_json(data, master_app.bot))
    return {"ok": True}


@app.post("/api/bot/{token}")
async def child_route(request: Request, token: str):
    data = await request.json()
    await process_child_update(token, data)
    return {"ok": True}


@app.get("/api/main")
async def health():
    return {"status":"active","keep_alive":"✅"}
