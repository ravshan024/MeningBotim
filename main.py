import os
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart, Command
import yt_dlp

BOT_TOKEN = "8926119680:AAELFYwSVdryZ9Uhpn4ikLV6I2qBJDzQsTE"
ADMIN_ID = 6489364078

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# DATABASE

db = sqlite3.connect("users.db")
sql = db.cursor()

sql.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")

db.commit()


# SAVE USER

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


# START

@dp.message(CommandStart())
async def start(message: Message):

    user = message.from_user

    save_user(user.id)

    await bot.send_message(
        ADMIN_ID,
        f"""
Yangi user

ID: {user.id}
Name: {user.full_name}
Username: @{user.username}
"""
    )

    await message.answer(
        "Instagram link yuboring"
    )


# DOWNLOAD

def download_instagram(url):

    ydl_opts = {
        "outtmpl": "%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(url, download=True)

        file_path = ydl.prepare_filename(info)

    return file_path


# DOWNLOADER

@dp.message(F.text)
async def downloader(message: Message):

    url = message.text

    if "instagram.com" not in url:

        await message.answer(
            "Faqat Instagram link yuboring"
        )

        return

    msg = await message.answer(
        "Yuklanmoqda..."
    )

    try:

        loop = asyncio.get_event_loop()

        file_path = await loop.run_in_executor(
            None,
            download_instagram,
            url
        )

        ext = file_path.split(".")[-1].lower()

        if ext == "mp4":

            video = FSInputFile(file_path)

            await message.answer_video(video)

        else:

            photo = FSInputFile(file_path)

            await message.answer_photo(photo)

        os.remove(file_path)

        await msg.delete()

    except Exception as e:

        await msg.edit_text(
            f"Xato: {e}"
        )


# STATS

@dp.message(Command("stats"))
async def stats(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    sql.execute(
        "SELECT COUNT(*) FROM users"
    )

    users = sql.fetchone()[0]

    await message.answer(
        f"Userlar soni: {users}"
    )


# BROADCAST

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
        f"Yuborildi: {success}"
    )


# MAIN

async def main():

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
