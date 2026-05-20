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
from aiohttp import web
import yt_dlp

# =====================================
# CONFIG
# =====================================

BOT_TOKEN = "8926119680:AAELFYwSVdryZ9Uhpn4ikLV6I2qBJDzQsTE"
ADMIN_ID = 6489364078
DOWNLOADS_DIR = "downloads"

os.makedirs(DOWNLOADS_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =====================================
# DATABASE
# =====================================

db = sqlite3.connect("users.db")
sql = db.cursor()

sql.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    username TEXT,
    join_date TEXT
)
""")

db.commit()

# =====================================
# SAVE USER
# =====================================

def save_user(user):

    sql.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user.id,)
    )

    exists = sql.fetchone()

    if exists is None:

        join_date = datetime.now().strftime(
            "%d.%m.%Y %H:%M"
        )

        sql.execute(
            """
            INSERT INTO users
            (user_id, full_name, username, join_date)
            VALUES (?, ?, ?, ?)
            """,
            (
                user.id,
                user.full_name,
                user.username,
                join_date
            )
        )

        db.commit()

# =====================================
# MENU
# =====================================

def get_menu(user_id):

    if user_id == ADMIN_ID:

        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="ℹ️ Yordam"
                    )
                ],
                [
                    KeyboardButton(
                        text="📊 Statistika"
                    )
                ]
            ],
            resize_keyboard=True
        )

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="ℹ️ Yordam"
                )
            ]
        ],
        resize_keyboard=True
    )

# =====================================
# START
# =====================================

@dp.message(CommandStart())
async def start(message: Message):

    save_user(message.from_user)

    await message.answer(
        """
🔥 Instagram Downloader

✅ Reels
✅ Story
✅ Post
✅ Video
✅ Rasm
✅ MP3

📥 Instagram link yuboring
""",
        reply_markup=get_menu(
            message.from_user.id
        )
    )

# =====================================
# HELP
# =====================================

@dp.message(F.text == "ℹ️ Yordam")
async def help_cmd(message: Message):

    await message.answer(
        """
📌 Instagram link yuboring

Misol:
https://www.instagram.com/reel/xxxxx
"""
    )

# =====================================
# STATS
# =====================================

@dp.message(F.text == "📊 Statistika")
@dp.message(Command("stats"))
async def stats(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    sql.execute(
        "SELECT * FROM users"
    )

    users = sql.fetchall()

    text = f"👥 Userlar: {len(users)}\n\n"

    for user in users[-10:]:

        text += (
            f"👤 {user[1]}\n"
            f"📛 @{user[2]}\n"
            f"🕒 {user[3]}\n\n"
        )

    await message.answer(text)

# =====================================
# DOWNLOAD MENU
# =====================================

@dp.message(F.text.contains("instagram.com"))
async def instagram_menu(message: Message):

    url = message.text.strip()

    buttons = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎬 Video",
                    callback_data=f"video|{url}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎵 MP3",
                    callback_data=f"mp3|{url}"
                )
            ]
        ]
    )

    await message.answer(
        "📥 Format tanlang",
        reply_markup=buttons
    )

# =====================================
# DOWNLOAD VIDEO
# =====================================

def download_video(url):

    options = {
        "format": "mp4",
        "outtmpl": f"{DOWNLOADS_DIR}/%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True
    }

    with yt_dlp.YoutubeDL(options) as ydl:

        info = ydl.extract_info(
            url,
            download=True
        )

        file_path = ydl.prepare_filename(info)

    return file_path

# =====================================
# DOWNLOAD MP3
# =====================================

def download_mp3(url):

    options = {
        "format": "bestaudio/best",
        "outtmpl": f"{DOWNLOADS_DIR}/%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320"
        }]
    }

    with yt_dlp.YoutubeDL(options) as ydl:

        info = ydl.extract_info(
            url,
            download=True
        )

        file_path = f"{DOWNLOADS_DIR}/{info['id']}.mp3"

    return file_path

# =====================================
# CALLBACKS
# =====================================

@dp.callback_query()
async def callbacks(call: CallbackQuery):

    data = call.data.split("|")

    action = data[0]
    url = data[1]

    await call.message.edit_text(
        "⏳ Yuklanmoqda..."
    )

    try:

        loop = asyncio.get_event_loop()

        # VIDEO

        if action == "video":

            file_path = await loop.run_in_executor(
                None,
                download_video,
                url
            )

            ext = file_path.split(".")[-1].lower()

            if ext in ["mp4", "mov"]:

                await call.message.answer_video(
                    FSInputFile(file_path)
                )

            else:

                await call.message.answer_photo(
                    FSInputFile(file_path)
                )

        # MP3

        elif action == "mp3":

            file_path = await loop.run_in_executor(
                None,
                download_mp3,
                url
            )

            await call.message.answer_audio(
                FSInputFile(file_path)
            )

        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:

        await call.message.answer(
            f"❌ Xato:\n{e}"
        )

# =====================================
# KEEP ALIVE
# =====================================

async def health(request):
    return web.Response(text="Bot ishlayapti")

# =====================================
# MAIN
# =====================================

async def main():

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    app = web.Application()

    app.router.add_get(
        "/",
        health
    )

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        int(os.environ.get("PORT", 10000))
    )

    await site.start()

    await dp.start_polling(bot)

# =====================================
# START APP
# =====================================

if __name__ == "__main__":

    asyncio.run(main())
