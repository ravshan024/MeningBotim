import os
import sqlite3
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart
from aiohttp import web
import yt_dlp

# =====================================
# SOZLAMALAR
# =====================================
BOT_TOKEN = "8926119680:AAELFYwSVdryZ9Uhpn4ikLV6I2qBJDzQsTE"
ADMIN_ID = 6489364078
DOWNLOADS_DIR = "downloads"

os.makedirs(DOWNLOADS_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =====================================
# BAZA VA MENU
# =====================================
db = sqlite3.connect("users.db")
sql = db.cursor()
sql.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, full_name TEXT, username TEXT, join_date TEXT)")
db.commit()

def get_menu(user_id):
    if user_id == ADMIN_ID:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="ℹ️ Yordam")], [KeyboardButton(text="📊 Statistika")]], resize_keyboard=True)
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="ℹ️ Yordam")]], resize_keyboard=True)

# =====================================
# YUKLASH FUNKSIYASI (FAQAT INSTAGRAM)
# =====================================
def download_insta(url):
    options = {
        "outtmpl": f"{DOWNLOADS_DIR}/%(id)s.%(ext)s",
        "quiet": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# =====================================
# HANDLERS
# =====================================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("👋 Salom! Menga Instagram post, Reels yoki Story havolasini yuboring.", reply_markup=get_menu(message.from_user.id))

@dp.message(F.text.contains("instagram.com"))
async def handle_insta(message: Message):
    url = message.text.strip()
    msg = await message.answer("⏳ Instagram'dan yuklanmoqda...")
    
    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_insta, url)
        
        if file_path.endswith(('.mp4', '.mov')):
            await message.answer_video(video=FSInputFile(file_path))
        else:
            await message.answer_photo(photo=FSInputFile(file_path))
        
        await msg.delete()
        if os.path.exists(file_path): os.remove(file_path)
    except Exception:
        await msg.edit_text("❌ Yuklashda xatolik! Profil yopiq bo'lishi mumkin.")

@dp.message(F.text == "ℹ️ Yordam")
async def help_cmd(message: Message):
    await message.answer("Faqat Instagram havolalarini yuboring (Reels, Post, Story).")

# =====================================
# RENDER SERVER
# =====================================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    # Render uchun portni tinglash
    app = web.Application()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 10000)))
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
