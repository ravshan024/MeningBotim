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
    CallbackQuery, InputMediaPhoto, InputMediaVideo,
)
from aiogram.filters import CommandStart, Command
from aiohttp import web
import yt_dlp

# ── CONFIG ────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID  = int(os.environ.get("ADMIN_ID", "0"))
PORT      = int(os.environ.get("PORT", 10000))
DOWN_DIR  = "downloads"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN muhit o'zgaruvchisi o'rnatilmagan!")

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

# ── YORDAMCHILAR ──────────────────────────────────────────
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

def get_menu(user_id):
    rows = [[KeyboardButton(text="ℹ️ Yordam")]]
    if user_id == ADMIN_ID:
        rows.append([KeyboardButton(text="📊 Statistika")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def store_url(url: str) -> str:
    sid = uuid.uuid4().hex[:12]
    url_cache[sid] = url
    return sid

# ── YT-DLP YUKLAB OLISH ───────────────────────────────────
YDL_COMMON = {
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

def download_video(url: str) -> list[str]:
    uid  = uuid.uuid4().hex[:10]
    opts = {
        **YDL_COMMON,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": f"{DOWN_DIR}/{uid}.%(ext)s",
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
        # merge bo'lganda ext mp4 bo'lishi shart
        if not path.endswith(".mp4"):
            path = f"{DOWN_DIR}/{uid}.mp4"
    return [path] if os.path.exists(path) else []

def download_mp3(url: str) -> list[str]:
    uid  = uuid.uuid4().hex[:10]
    path = f"{DOWN_DIR}/{uid}.mp3"
    opts = {
        **YDL_COMMON,
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
    return [path] if os.path.exists(path) else []

# ── HANDLERLAR ────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(msg: Message):
    save_user(msg.from_user)
    await msg.answer(
        "🔥 <b>Instagram Downloader</b>\n\n"
        "✅ Reels · Post · Video · Rasm · MP3\n\n"
        "📥 Instagram linkini yuboring:",
        parse_mode="HTML",
        reply_markup=get_menu(msg.from_user.id)
    )

@dp.message(F.text == "ℹ️ Yordam")
async def cmd_help(msg: Message):
    await msg.answer(
        "📌 <b>Foydalanish</b>\n\n"
        "1. Instagram linkini nusxalang\n"
        "2. Botga yuboring\n"
        "3. Video yoki MP3 tanlang\n\n"
        "<b>Ishlaydi:</b>\n"
        "• instagram.com/reel/...\n"
        "• instagram.com/p/...\n"
        "• instagram.com/tv/...",
        parse_mode="HTML"
    )

@dp.message(F.text == "📊 Statistika")
@dp.message(Command("stats"))
async def cmd_stats(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    lines = "\n".join(
        f"👤 {u[1]}  @{u[2]}  {u[3]}" for u in users[-20:]
    )
    await msg.answer(
        f"👥 Jami: <b>{len(users)}</b> foydalanuvchi\n\n{lines}",
        parse_mode="HTML"
    )

@dp.message(Command("broadcast"))
async def cmd_broadcast(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    text = msg.text.removeprefix("/broadcast").strip()
    if not text:
        return await msg.answer("❗ /broadcast <xabar>")
    cur.execute("SELECT user_id FROM users")
    ok = 0
    for (uid,) in cur.fetchall():
        try:
            await bot.send_message(uid, text)
            ok += 1
        except Exception:
            pass
    await msg.answer(f"✅ {ok} ta foydalanuvchiga yuborildi")

@dp.message(F.text.contains("instagram.com"))
async def handle_link(msg: Message):
    url = msg.text.strip()
    sid = store_url(url)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Video", callback_data=f"v|{sid}")],
        [InlineKeyboardButton(text="🎵 MP3",   callback_data=f"m|{sid}")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data=f"c|{sid}")],
    ])
    await msg.answer("📥 Format tanlang:", reply_markup=kb)

@dp.callback_query()
async def handle_cb(call: CallbackQuery):
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

    files: list[str] = []
    try:
        loop  = asyncio.get_event_loop()
        fn    = download_mp3 if action == "m" else download_video
        files = await loop.run_in_executor(None, fn, url)

        if not files:
            await call.message.edit_text("❌ Fayl topilmadi")
            return

        path = files[0]
        if path.endswith(".mp4"):
            await call.message.answer_video(FSInputFile(path))
        elif path.endswith(".mp3"):
            await call.message.answer_audio(FSInputFile(path))
        else:
            await call.message.answer_photo(FSInputFile(path))

        await call.message.edit_text("✅ Yuklab olindi!")

    except Exception as e:
        log.error(e)
        await call.message.edit_text(
            f"❌ Xato:\n<code>{str(e)[:300]}</code>",
            parse_mode="HTML"
        )
    finally:
        for f in files:
            try:
                os.remove(f)
            except Exception:
                pass
        url_cache.pop(sid, None)

# ── RENDER.COM UCHUN WEB SERVER ───────────────────────────
async def health(request):
    return web.Response(text="OK")

async def run_web():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info(f"Web server: 0.0.0.0:{PORT}")

# ── MAIN ──────────────────────────────────────────────────
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await run_web()
    log.info("Bot ishga tushdi ✅")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
