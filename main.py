import os
import uuid
import sqlite3
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, FSInputFile,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.filters import CommandStart
from aiohttp import web
import yt_dlp

# ── CONFIG ────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8926119680:AAElC7nnDwNvyTKOFqt7cGNGRYjAN8SYDSw")
ADMIN_ID  = int(os.environ.get("ADMIN_ID", "6489364078"))
PORT      = int(os.environ.get("PORT", 10000))
DOWN_DIR  = "downloads"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN o'rnatilmagan!")

os.makedirs(DOWN_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

# ── URL CACHE (64-bayt cheklov yechimi) ───────────────────
url_cache: dict[str, str] = {}

# ── DATABASE ──────────────────────────────────────────────
con = sqlite3.connect("users.db")
cur = con.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id   INTEGER PRIMARY KEY,
        full_name TEXT,
        username  TEXT,
        join_date TEXT
    )
""")
con.commit()

def save_user(user):
    cur.execute("SELECT 1 FROM users WHERE user_id=?", (user.id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users VALUES (?,?,?,?)",
            (user.id, user.full_name,
             user.username or "—",
             datetime.now().strftime("%d.%m.%Y %H:%M"))
        )
        con.commit()

# ── YUKLAB OLISH ──────────────────────────────────────────
YDL_BASE = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "socket_timeout": 30,
    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    },
}

def dl_video(url: str) -> str:
    uid = uuid.uuid4().hex[:10]
    out = f"{DOWN_DIR}/{uid}.mp4"
    opts = {
        **YDL_BASE,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": f"{DOWN_DIR}/{uid}.%(ext)s",
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
        if not os.path.exists(path):
            path = out
    return path

def dl_photo(url: str) -> str:
    uid = uuid.uuid4().hex[:10]
    opts = {
        **YDL_BASE,
        "format": "best",
        "outtmpl": f"{DOWN_DIR}/{uid}.%(ext)s",
        "writethumbnail": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        thumb = info.get("thumbnail", "")
    # thumbnail ni yuklaymiz
    import urllib.request
    ext  = thumb.split("?")[0].rsplit(".", 1)[-1] or "jpg"
    path = f"{DOWN_DIR}/{uid}.{ext}"
    urllib.request.urlretrieve(thumb, path)
    return path

def dl_mp3(url: str) -> str:
    uid  = uuid.uuid4().hex[:10]
    path = f"{DOWN_DIR}/{uid}.mp3"
    opts = {
        **YDL_BASE,
        "format": "bestaudio/best",
        "outtmpl": f"{DOWN_DIR}/{uid}.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)
    return path

# ── MENU ──────────────────────────────────────────────────
def menu(uid):
    rows = [[KeyboardButton(text="ℹ️ Yordam")]]
    if uid == ADMIN_ID:
        rows.append([KeyboardButton(text="📊 Statistika")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

# ── HANDLERLAR ────────────────────────────────────────────
@dp.message(CommandStart())
async def start(msg: Message):
    save_user(msg.from_user)
    await msg.answer(
        "🔥 <b>Instagram Downloader</b>\n\n"
        "📥 Instagram linkini yuboring:",
        parse_mode="HTML",
        reply_markup=menu(msg.from_user.id)
    )

@dp.message(F.text == "ℹ️ Yordam")
async def help_cmd(msg: Message):
    await msg.answer(
        "📌 Instagram linkini yuboring\n\n"
        "Keyin format tanlang:\n"
        "🎬 Video · 🖼 Rasm · 🎵 MP3"
    )

@dp.message(F.text == "📊 Statistika")
async def stats(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    text  = f"👥 Jami: <b>{len(users)}</b> foydalanuvchi\n\n"
    for u in users[-15:]:
        text += f"👤 {u[1]}  @{u[2]}  {u[3]}\n"
    await msg.answer(text, parse_mode="HTML")

@dp.message(F.text.contains("instagram.com"))
async def link(msg: Message):
    save_user(msg.from_user)
    url = msg.text.strip()
    sid = uuid.uuid4().hex[:12]
    url_cache[sid] = url
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Video", callback_data=f"v|{sid}"),
            InlineKeyboardButton(text="🖼 Rasm",  callback_data=f"p|{sid}"),
            InlineKeyboardButton(text="🎵 MP3",   callback_data=f"m|{sid}"),
        ],
        [InlineKeyboardButton(text="❌ Bekor", callback_data=f"c|{sid}")],
    ])
    await msg.answer("📥 Format tanlang:", reply_markup=kb)

@dp.callback_query()
async def callback(call: CallbackQuery):
    action, sid = call.data.split("|", 1)

    if action == "c":
        url_cache.pop(sid, None)
        await call.message.delete()
        return

    url = url_cache.get(sid)
    if not url:
        await call.answer("❗ Link eskirdi, qayta yuboring", show_alert=True)
        return

    await call.message.edit_text("⏳ Yuklanmoqda...")

    path = None
    try:
        loop = asyncio.get_event_loop()

        if action == "v":
            path = await loop.run_in_executor(None, dl_video, url)
            await call.message.answer_video(FSInputFile(path))
        elif action == "p":
            path = await loop.run_in_executor(None, dl_photo, url)
            await call.message.answer_photo(FSInputFile(path))
        elif action == "m":
            path = await loop.run_in_executor(None, dl_mp3, url)
            await call.message.answer_audio(FSInputFile(path))

        await call.message.edit_text("✅ Tayyor!")

    except Exception as e:
        log.error(e)
        await call.message.edit_text(
            f"❌ Xato:\n<code>{str(e)[:300]}</code>",
            parse_mode="HTML"
        )
    finally:
        if path and os.path.exists(path):
            os.remove(path)
        url_cache.pop(sid, None)

# ── 24/7 UCHUN WEB SERVER ─────────────────────────────────
async def health(request):
    return web.Response(text="OK")

async def run_web():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()

# ── MAIN ──────────────────────────────────────────────────
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await run_web()
    log.info("Bot ishga tushdi ✅")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
