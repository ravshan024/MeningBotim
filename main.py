import os
import sqlite3
import asyncio
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

BOT_TOKEN = "8926119680:AAELFYwSVdryZ9Uhpn4ikLV6I2qBJDzQsTE"
ADMIN_ID = 6489364078

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

        menu = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="📥 Instagram Yuklash"
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

    else:

        menu = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="📥 Instagram Yuklash"
                    )
                ]
            ],
            resize_keyboard=True
        )

    return menu

# =====================================
# START
# =====================================

@dp.message(CommandStart())
async def start(message: Message):

    user = message.from_user

    save_user(user)

    await message.answer(
        """
🔥 Instagram Downloader Bot

✅ Video
✅ Reels
✅ Post
✅ Story
✅ Rasm
✅ MP3

📥 Instagram link yuboring
""",
        reply_markup=get_menu(user.id)
    )

# =====================================
# STATS BUTTON
# =====================================

@dp.message(F.text == "📊 Statistika")
async def stats_button(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    sql.execute(
        "SELECT * FROM users"
    )

    users = sql.fetchall()

    text = f"👥 Userlar soni: {len(users)}\n\n"

    for user in users[-10:]:

        text += (
            f"👤 {user[1]}\n"
            f"📛 @{user[2]}\n"
            f"🕒 {user[3]}\n"
            f"🆔 {user[0]}\n\n"
        )

    await message.answer(text)

# =====================================
# DOWNLOAD MENU
# =====================================

@dp.message(F.text)
async def downloader(message: Message):

    url = message.text

    if "instagram.com" not in url:
        return

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
# VIDEO DOWNLOAD
# =====================================

def download_video(url):

    ydl_opts = {
        "format": "mp4",
        "outtmpl": "%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            url,
            download=True
        )

        file_path = ydl.prepare_filename(info)

    return file_path

# =====================================
# MP3 DOWNLOAD
# =====================================

def download_mp3(url):

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320"
        }]
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            url,
            download=True
        )

        title = info["title"]

        file_path = f"{title}.mp3"

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

            if ext == "mp4":

                video = FSInputFile(file_path)

                await call.message.answer_video(
                    video
                )

            else:

                photo = FSInputFile(file_path)

                await call.message.answer_photo(
                    photo
                )

        # MP3

        elif action == "mp3":

            file_path = await loop.run_in_executor(
                None,
                download_mp3,
                url
            )

            audio = FSInputFile(file_path)

            await call.message.answer_audio(
                audio
            )

        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:

        await call.message.answer(
            f"❌ Xato:\n{e}"
        )

# =====================================
# /stats
# =====================================

@dp.message(Command("stats"))
async def stats(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    sql.execute(
        "SELECT * FROM users"
    )

    users = sql.fetchall()

    text = f"👥 Userlar soni: {len(users)}\n\n"

    for user in users[-10:]:

        text += (
            f"👤 {user[1]}\n"
            f"📛 @{user[2]}\n"
            f"🕒 {user[3]}\n"
            f"🆔 {user[0]}\n\n"
        )

    await message.answer(text)

# =====================================
# BROADCAST
# =====================================

@dp.message(Command("broadcast"))
async def broadcast(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    text = message.text.replace(
        "/broadcast ",
        ""
    )

    sql.execute(
        "SELECT user_id FROM users"
    )

    users = sql.fetchall()

    success = 0

    for user in users:

        try:

            await bot.send_message(
                user[0],
                text
            )

            success += 1

        except:
            pass

    await message.answer(
        f"✅ Yuborildi: {success}"
    )

# =====================================
# MAIN
# =====================================

async def main():

    await dp.start_polling(bot)

if __name__ == "__main__":

    asyncio.run(main())
