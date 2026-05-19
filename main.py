import os
import sqlite3
import asyncio
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

# =========================
# CONFIG
# =========================

BOT_TOKEN = "8926119680:AAELFYwSVdryZ9Uhpn4ikLV6I2qBJDzQsTE"
ADMIN_ID = 6489364078

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =========================
# DATABASE
# =========================

db = sqlite3.connect("users.db")
sql = db.cursor()

sql.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")

db.commit()

# =========================
# SAVE USER
# =========================

def save_user(user_id):

    sql.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    )

    user = sql.fetchone()

    if user is None:

        sql.execute(
            "INSERT INTO users VALUES (?)",
            (user_id,)
        )

        db.commit()

# =========================
# MENU
# =========================

menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="📥 Instagram yuklash"
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

# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):

    user = message.from_user

    save_user(user.id)

    await bot.send_message(
        ADMIN_ID,
        f"""
🔥 Yangi user

🆔 ID: {user.id}
👤 Name: {user.full_name}
📛 Username: @{user.username}
"""
    )

    await message.answer(
        """
👋 Instagram Downloader Bot

📥 Reels
🖼 Rasm
📺 Story
🎬 Video
🎵 MP3

Instagram link yuboring.
""",
        reply_markup=menu
    )

# =========================
# STATS BUTTON
# =========================

@dp.message(F.text == "📊 Statistika")
async def statistics(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    sql.execute(
        "SELECT COUNT(*) FROM users"
    )

    users = sql.fetchone()[0]

    await message.answer(
        f"""
📊 Statistika

👥 Userlar: {users}
"""
    )

# =========================
# LINK HANDLER
# =========================

@dp.message(F.text)
async def get_link(message: Message):

    url = message.text

    if "instagram.com" not in url:

        await message.answer(
            "❌ Instagram link yuboring"
        )

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

# =========================
# DOWNLOAD VIDEO
# =========================

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

# =========================
# DOWNLOAD MP3
# =========================

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

# =========================
# CALLBACKS
# =========================

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

            video = FSInputFile(file_path)

            await call.message.answer_video(
                video
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

        os.remove(file_path)

    except Exception as e:

        await call.message.answer(
            f"❌ Xato:\n{e}"
        )

# =========================
# /stats
# =========================

@dp.message(Command("stats"))
async def stats(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    sql.execute(
        "SELECT COUNT(*) FROM users"
    )

    users = sql.fetchone()[0]

    await message.answer(
        f"👥 Userlar soni: {users}"
    )

# =========================
# /broadcast
# =========================

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

# =========================
# MAIN
# =========================

async def main():

    await dp.start_polling(bot)

if __name__ == "__main__":

    asyncio.run(main())
