import os
import json
import httpx

# Firebase Realtime Database
DB_URL    = os.environ.get("DB_URL", "")
DB_SECRET = os.environ.get("DB_SECRET", "")

def fb_url(path):
    return f"{DB_URL}/{path}.json?auth={DB_SECRET}"

async def db_get(path):
    if not DB_URL: return None
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.get(fb_url(path))
            return r.json() if r.status_code == 200 else None
        except: return None

async def db_put(path, data):
    if not DB_URL: return False
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.put(fb_url(path), json=data)
            return r.status_code == 200
        except: return False

async def db_patch(path, data):
    if not DB_URL: return False
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.patch(fb_url(path), json=data)
            return r.status_code == 200
        except: return False

async def db_del(path):
    if not DB_URL: return False
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.delete(fb_url(path))
            return r.status_code == 200
        except: return False

async def send_tg(token, method, payload):
    async with httpx.AsyncClient(timeout=12) as c:
        try:
            r = await c.post(
                f"https://api.telegram.org/bot{token}/{method}",
                json=payload
            )
            return r.json()
        except: return {"ok": False}
