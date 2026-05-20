import os
import sqlite3
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    FSInputFile,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.filters import CommandStart, Command
import yt_dlp

# =====================================
# CONFIG
# =====================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8926119680:AAFrKDnlW8Fbe1IXoKESl1CTN8_QbxPDjIE")
ADMIN_ID   = int(os.environ.get("ADMIN_ID", "6489364078"))
DOWN_DIR   = "downloads"

os.makedirs(DOWN_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

# =====================================
# DATABASE
# =====================================

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

# =====================================
# YORDAMCHI FUNKSIYALAR
# =====================================

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


def ydl_download(url: str, fmt: str) -> str:
    """
    fmt = 'video' yoki 'mp3'
    Muvaffaqiyatli bo'lsa fayl yo'lini qaytaradi,
    xato bo'lsa Exception ko'taradi.
    """
    uid = str(abs(hash(url)))[:10]

    if fmt == "video":
        opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": f"{DOWN_DIR}/{uid}.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "merge_output_format": "mp4",
        }
    else:  # mp3
        opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{DOWN_DIR}/{uid}.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if fmt == "mp3":
            return f"{DOWN_DIR}/{uid}.mp3"
        return ydl.prepare_filename(info)

# =====================================
# HANDLERLAR
# =====================================

@dp.message(CommandStart())
async def cmd_start(msg: Message):
    save_user(msg.from_user)
    await msg.answer(
        "🔥 <b>Instagram Downloader</b>\n\n"
        "✅ Reels · Post · Story\n"
        "✅ Video · Rasm · MP3\n\n"
        "📥 Instagram linkini yuboring:",
        parse_mode="HTML",
        reply_markup=get_menu(msg.from_user.id)
    )


@dp.message(F.text == "ℹ️ Yordam")
async def cmd_help(msg: Message):
    await msg.answer(
        "📌 <b>Qo'llanma</b>\n\n"
        "1. Instagram linkini ko'chiring\n"
        "2. Botga yuboring\n"
        "3. Video yoki MP3 tanlang\n\n"
        "<b>Misol:</b>\n"
        "https://www.instagram.com/reel/ABC123/",
        parse_mode="HTML"
    )


@dp.message(F.text == "📊 Statistika")
@dp.message(Command("stats"))
async def cmd_stats(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    text = f"👥 Jami: <b>{len(users)}</b> ta foydalanuvchi\n\n"
    for u in users[-10:]:
        text += f"👤 {u[1]}  |  @{u[2]}  |  {u[3]}\n"
    await msg.answer(text, parse_mode="HTML")


@dp.message(Command("broadcast"))
async def cmd_broadcast(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    text = msg.text.removeprefix("/broadcast").strip()
    if not text:
        await msg.answer("❗ Matn kiriting: /broadcast <xabar>")
        return
    cur.execute("SELECT user_id FROM users")
    ok = 0
    for (uid,) in cur.fetchall():
        try:
            await bot.send_message(uid, text)
            ok += 1
        except Exception:
            pass
    await msg.answer(f"✅ Yuborildi: {ok} ta")


@dp.message(F.text.contains("instagram.com"))
async def handle_link(msg: Message):
    url = msg.text.strip()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Video", callback_data=f"video|{url}")],
        [InlineKeyboardButton(text="🎵 MP3",   callback_data=f"mp3|{url}")],
    ])
    await msg.answer("📥 Format tanlang:", reply_markup=kb)


@dp.callback_query()
async def handle_callback(call: CallbackQuery):
    parts  = call.data.split("|", 1)
    fmt    = parts[0]
    url    = parts[1]

    await call.message.edit_text("⏳ Yuklanmoqda...")

    file_path = None
    try:
        loop      = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, ydl_download, url, fmt)

        if fmt == "video":
            ext = file_path.rsplit(".", 1)[-1].lower()
            if ext in ("mp4", "mov", "mkv"):
                await call.message.answer_video(FSInputFile(file_path))
            else:
                await call.message.answer_photo(FSInputFile(file_path))
        else:
            await call.message.answer_audio(FSInputFile(file_path))

        await call.message.edit_text("✅ Tayyor!")

    except Exception as e:
        log.error(e)
        await call.message.edit_text(f"❌ Xato:\n<code>{str(e)[:200]}</code>",
                                     parse_mode="HTML")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# =====================================
# MAIN
# =====================================

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Bot ishga tushdi ✅")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
