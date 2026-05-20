import os
import sqlite3
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, FSInputFile, ReplyKeyboardMarkup,
    KeyboardButton, InlineKeyboardMarkup,
    InlineKeyboardButton, CallbackQuery
)
from aiogram.filters import CommandStart, Command
from aiohttp import web
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
    sql.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
    exists = sql.fetchone()

    if exists is None:
        join_date = datetime.now().strftime("%d.%m.%Y %H:%M")
        sql.execute(
            "INSERT INTO users (user_id, full_name, username, join_date) VALUES (?, ?, ?, ?)",
            (user.id, user.full_name, user.username, join_date)
        )
        db.commit()

# =====================================
# MENU
# =====================================
def get_menu(user_id):
    if user_id == ADMIN_ID:
        menu = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📥 Instagram Yuklash")],
                [KeyboardButton(text="📊 Statistika")]
            ],
            resize_keyboard=True
        )
    else:
        menu = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📥 Instagram Yuklash")]
            ],
            resize_keyboard=True
        )
    return menu

# =====================================
# START
# =====================================
@dp.message(CommandStart())
async def start(message: Message):
    save_user(message.from_user)
    await message.answer(
        "🔥 **Instagram Downloader Bot**\n\n"
        "✅ Video\n✅ Reels\n✅ Post\n✅ Story\n✅ Rasm\n✅ MP3\n\n"
        "📥 Instagram link yuboring",
        reply_markup=get_menu(message.from_user.id)
    )

# =====================================
# STATS BUTTON
# =====================================
@dp.message(F.text == "📊 Statistika")
async def stats_button(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    sql.execute("SELECT * FROM users")
    users = sql.fetchall()

    text = f"👥 Userlar soni: {len(users)}\n\n"
    for user in users[-10:]:
        text += f"👤 {user[1]}\n📛 @{user[2]}\n🕒 {user[3]}\n🆔 {user[0]}\n\n"

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
            [InlineKeyboardButton(text="🎬 Video", callback_data=f"video|{url}")],
            [InlineKeyboardButton(text="🎵 MP3", callback_data=f"mp3|{url}")]
        ]
    )
    await message.answer("📥 Format tanlang", reply_markup=buttons)

# =====================================
# VIDEO DOWNLOAD
# =====================================
def download_video(url):
    ydl_opts = {
        "format": "mp4/best",
        "outtmpl": "%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
    return file_path

# =====================================
# MP3 DOWNLOAD
# =====================================
def download_mp3(url):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }],
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # yt-dlp renames the file after extraction when using FFmpegExtractAudio
        file_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
    return file_path

# =====================================
# CALLBACKS
# =====================================
@dp.callback_query()
async def callbacks(call: CallbackQuery):
    data = call.data.split("|", 1)
    if len(data) != 2: return
    
    action, url = data
    await call.message.edit_text("⏳ Yuklanmoqda...")

    try:
        loop = asyncio.get_event_loop()
        if action == "video":
            file_path = await loop.run_in_executor(None, download_video, url)
            ext = file_path.split(".")[-1].lower()
            if ext in ["mp4", "webm"]:
                await call.message.answer_video(FSInputFile(file_path))
            else:
                await call.message.answer_photo(FSInputFile(file_path))
                
        elif action == "mp3":
            file_path = await loop.run_in_executor(None, download_mp3, url)
            await call.message.answer_audio(FSInputFile(file_path))

        await call.message.delete()
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        await call.message.edit_text(f"❌ Yuklashda xatolik yuz berdi. Profil yopiq bo'lishi mumkin.")

# =====================================
# BROADCAST
# =====================================
@dp.message(Command("broadcast"))
async def broadcast(message: Message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.replace("/broadcast ", "")
    sql.execute("SELECT user_id FROM users")
    users = sql.fetchall()
    
    success = 0
    for user in users:
        try:
            await bot.send_message(user[0], text)
            success += 1
            await asyncio.sleep(0.05) # Telegram bloklamasligi uchun pauza
        except:
            pass
    await message.answer(f"✅ Yuborildi: {success}")

# =====================================
# RENDER SERVER UCHUN MUXIM QISM
# =====================================
async def handle_ping(request):
    return web.Response(text="Bot ishlayapti!")

async def main():
    # Eski webhookni tozalash (Conflict xatosini yo'qotadi)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Render qotib qolmasligi uchun fon serveri
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    # Botni ishga tushirish
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
