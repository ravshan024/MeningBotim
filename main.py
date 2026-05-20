import os
import sqlite3
import asyncio
import logging
# timedelta qo'shildi, vaqtni surish uchun
from datetime import datetime, timezone, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiohttp import web
import yt_dlp

# =====================================
# SOZLAMALAR (CONFIG)
# =====================================
BOT_TOKEN = "8926119680:AAElC7nnDwNvyTKOFqt7cGNGRYjAN8SYDSw"
ADMIN_ID = 6489364078  
DOWNLOADS_DIR = "downloads"
TG_MAX_SIZE = 50 * 1024 * 1024  

os.makedirs(DOWNLOADS_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =====================================
# O'ZBEKISTON VAQTINI HISOBLASH FUNKSIYASI
# =====================================
def get_uzb_time():
    # Render vaqti (UTC) ga 5 soat qo'shib, aynan Toshkent vaqtini hosil qilamiz
    return (datetime.utcnow() + timedelta(hours=5)).strftime("%d.%m.%Y %H:%M:%S")

# =====================================
# MA'LUMOTLAR BAZASI (DATABASE)
# =====================================
db = sqlite3.connect("users.db")
sql = db.cursor()
sql.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, full_name TEXT, username TEXT, join_date TEXT)")
db.commit()

def save_user(user):
    try:
        sql.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
        if sql.fetchone() is None:
            # Toshkent vaqtini aniq hisoblab bazaga yozamiz
            tz_uzb = timezone(timedelta(hours=5))
            uzb_time = datetime.now(tz_uzb).strftime("%d.%m.%Y %H:%M")
            
            sql.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user.id, user.full_name, user.username, uzb_time))
            db.commit()
    except Exception as e:
        logging.error(f"Bazaga saqlashda xatolik: {e}")
        
# =====================================
# YUKLOVCHI TIZIM (DOWNLOADER)
# =====================================
def download_insta(url):
    options = {
        "outtmpl": f"{DOWNLOADS_DIR}/%(id)s.%(ext)s",
        "quiet": True,
        "format": "best",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# =====================================
# FAYLNI YUBORISH VA BO'LISH
# =====================================
async def send_file(chat_id, path):
    size = os.path.getsize(path)
    if size <= TG_MAX_SIZE:
        await bot.send_video(chat_id, video=FSInputFile(path))
    else:
        await bot.send_message(chat_id, "⚠️ Fayl 50MB dan katta, qismlarga bo'linmoqda...")
        part_size = 45 * 1024 * 1024
        with open(path, "rb") as f:
            part_num = 1
            while chunk := f.read(part_size):
                p_path = f"{path}_part{part_num}.mp4"
                with open(p_path, "wb") as pf: 
                    pf.write(chunk)
                await bot.send_document(chat_id, document=FSInputFile(p_path), caption=f"Qism {part_num}")
                os.remove(p_path)
                part_num += 1
    os.remove(path)

# =====================================
# 1. START BUYRUG'I
# =====================================
@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
    
    sql.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    is_new_user = sql.fetchone() is None
    
    save_user(message.from_user)
    
    # Mana shu yerda probellar (chekinishlar) aniq 4 ta bo'shliq bilan to'g'rilandi:
    await message.answer(
        "👋 Instagram downloader botiga xush kelibsiz!\n\nLink yuboring.", 
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="ℹ️ Yordam")]
            ], 
            resize_keyboard=True
        )
    )
    
    if is_new_user and user_id != ADMIN_ID:
        tz_uzb = timezone(timedelta(hours=5))
        current_time = datetime.now(tz_uzb).strftime("%d.%m.%Y %H:%M:%S")
        admin_msg = (
            f"🥳 <b>Yangi foydalanuvchi botni boshladi!</b>\n\n"
            f"👤 Ismi: {full_name}\n"
            f"Username: {username}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"🕒 <b>Vaqt:</b> {current_time}"
        )
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Adminga start xabarini yuborishda xatolik: {e}")

# =====================================
# 2. LINK KELGANDA
# =====================================
@dp.message(F.text.contains("instagram.com"))
async def handle_link(message: Message):
    # Yangi funksiyadan to'g'ri vaqtni olamiz
    current_time = get_uzb_time()
    user_name = message.from_user.full_name
    username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
    
    if message.from_user.id != ADMIN_ID:
        report_msg = (
            f"📥 <b>Botdan foydalanildi!</b>\n\n"
            f"👤 <b>Kim:</b> {user_name} ({username})\n"
            f"🕒 <b>Vaqt:</b> {current_time}\n"
            f"🔗 <b>Link:</b> {message.text}"
        )
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=report_msg, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            logging.error(f"Adminga hisobot yuborishda xatolik: {e}")

    msg = await message.answer("⏳ Navbatga qo'shildi, yuklanmoqda...")
    try:
        loop = asyncio.get_event_loop()
        path = await loop.run_in_executor(None, download_insta, message.text)
        await msg.edit_text("✅ Yuklandi! Yuborilmoqda...")
        await send_file(message.chat.id, path)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ Xato: {e}")

# =====================================
# RENDER SERVER VA ISHGA TUSHIRISH
# =====================================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    app = web.Application()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 10000)))
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    # =====================================
# STATISTIKA TUGMASI ISHLASHI
# =====================================
@dp.message(F.text == "📊 Statistika")
async def show_stats(message: Message):
    # Faqat siz (admin) ko'ra olishingiz uchun tekshiramiz
    if message.from_user.id == ADMIN_ID:
        try:
            sql.execute("SELECT COUNT(*) FROM users")
            total_users = sql.fetchone()[0]
            
            await message.answer(f"📊 <b>Bot statistikasi:</b>\n\n👤 Jami foydalanuvchilar: <b>{total_users} ta</b>", parse_mode="HTML")
        except Exception as e:
            await message.answer(f"❌ Statistikani hisoblashda xatolik: {e}")
    else:
        # Agar oddiy foydalanuvchi bossa, unga shunchaki havola yuborishni eslatadi
        await message.answer("📥 Menga Instagram link yuboring, men uni yuklab beraman!")

    asyncio.run(main())
        
