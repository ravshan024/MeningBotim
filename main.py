import os
import sqlite3
import asyncio
import logging
import datetime

import aiogram
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiohttp import web
import yt_dlp

# =====================================
# SOZLAMALAR (CONFIG)
# =====================================
BOT_TOKEN = "8926119680:AAELFYwSVdryZ9Uhpn4ikLV6I2qBJDzQsTE"
ADMIN_ID = 6489364078  
DOWNLOADS_DIR = "downloads"
TG_MAX_SIZE = 50 * 1024 * 1024  

os.makedirs(DOWNLOADS_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =====================================
# O'ZBEKISTON VAQTINI OLISH FUNKSIYASI
# =====================================
def get_uzb_time(with_seconds=True):
    tz = datetime.timezone(datetime.timedelta(hours=5))
    if with_seconds:
        return datetime.datetime.now(tz).strftime("%d.%m.%Y %H:%M:%S")
    return datetime.datetime.now(tz).strftime("%d.%m.%Y %H:%M")

def get_uzb_date():
    tz = datetime.timezone(datetime.timedelta(hours=5))
    return datetime.datetime.now(tz).strftime("%d.%m.%Y")

# =====================================
# MA'LUMOTLAR BAZASI (DATABASE)
# =====================================
db = sqlite3.connect("users.db")
sql = db.cursor()

# Jadvalni ustunlar nomi bilan aniq yaratamiz
sql.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY, 
    full_name TEXT, 
    username TEXT, 
    join_date TEXT,
    status TEXT DEFAULT 'bepul',
    daily_count INTEGER DEFAULT 0,
    last_active_date TEXT DEFAULT ''
)""")

# Agar eski baza mavjud bo'lsa va ustunlar yetishmasa, xavfsiz qo'shamiz
try:
    sql.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'bepul'")
except sqlite3.OperationalError:
    pass
try:
    sql.execute("ALTER TABLE users ADD COLUMN daily_count INTEGER DEFAULT 0")
except sqlite3.OperationalError:
    pass
try:
    sql.execute("ALTER TABLE users ADD COLUMN last_active_date TEXT DEFAULT ''")
except sqlite3.OperationalError:
    pass
db.commit()

def save_user(user):
    try:
        sql.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
        if sql.fetchone() is None:
            uzb_time_short = get_uzb_time(with_seconds=False)
            current_date = get_uzb_date()
            # Ustunlar nomini aniq yozib, xatolikni oldini olamiz
            sql.execute(
                "INSERT INTO users (user_id, full_name, username, join_date, status, daily_count, last_active_date) VALUES (?, ?, ?, ?, 'bepul', 0, ?)", 
                (user.id, user.full_name, user.username, uzb_time_short, current_date)
            )
            db.commit()
            return True # Yangi user qo'shildi
        return False # Eski user
    except Exception as e:
        logging.error(f"Bazaga saqlashda xatolik: {e}")
        return False

def check_and_update_limit(user_id):
    current_date = get_uzb_date()
    sql.execute("SELECT status, daily_count, last_active_date FROM users WHERE user_id=?", (user_id,))
    res = sql.fetchone()
    
    if not res:
        return True, "bepul"
        
    status, daily_count, last_active_date = res
    if status == 'premium':
        return True, "premium"
        
    # Yangi kun kelgan bo'lsa limitni 1 qilib yangilaymiz
    if last_active_date != current_date:
        sql.execute("UPDATE users SET daily_count = 1, last_active_date = ? WHERE user_id = ?", (current_date, user_id))
        db.commit()
        return True, "bepul"
        
    # Agar limit tugagan bo'lsa
    if daily_count >= 3:
        return False, "bepul"
        
    # Aks holda limitni bittaga oshiramiz
    sql.execute("UPDATE users SET daily_count = daily_count + 1 WHERE user_id = ?", (user_id,))
    db.commit()
    return True, "bepul"

# =====================================
# YUKLOVCHI TIZIM
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

async def send_file(chat_id, path, is_premium=False):
    size = os.path.getsize(path)
    caption_text = "\n\n📥 @MeningBotim orqali yuklandi" if not is_premium else ""
    
    if size <= TG_MAX_SIZE:
        await bot.send_video(chat_id, video=FSInputFile(path), caption=caption_text)
    else:
        await bot.send_message(chat_id, "⚠️ Fayl 50MB dan katta, qismlarga bo'linmoqda...")
        part_size = 45 * 1024 * 1024
        with open(path, "rb") as f:
            part_num = 1
            while chunk := f.read(part_size):
                p_path = f"{path}_part{part_num}.mp4"
                with open(p_path, "wb") as pf: 
                    pf.write(chunk)
                await bot.send_document(chat_id, document=FSInputFile(p_path), caption=f"Qism {part_num}{caption_text}")
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
    
    # save_user endi True yoki False qaytaradi, shu orqali dublikat oldi olinadi
    is_new_user = save_user(message.from_user)
    
    btn = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="⭐ Premium sotib olish")]
        ], 
        resize_keyboard=True
    )
    
    await message.answer("👋 Instagram downloader botiga xush kelibsiz!\n\nLink yuboring.", reply_markup=btn)
    
    # Faqat rostdan ham yangi odam kirgandagina adminga xabar boradi
    if is_new_user and user_id != ADMIN_ID:
        current_time = get_uzb_time(with_seconds=True)
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
# 2. STATISTIKA TUGMASI
# =====================================
@dp.message(F.text == "📊 Statistika")
async def show_stats(message: Message):
    if message.from_user.id == ADMIN_ID:
        try:
            sql.execute("SELECT COUNT(*) FROM users")
            total_users = sql.fetchone()[0]
            
            sql.execute("SELECT full_name, username, join_date, status FROM users ORDER BY rowid DESC LIMIT 10")
            recent_users = sql.fetchall()
            
            user_list = ""
            for i, u in enumerate(recent_users, 1):
                uname = u[1] if u[1] else "@mavjud_emas"
                badge = "⭐" if u[3] == "premium" else "👤"
                user_list += f"{i}. {badge} {u[0]} ({uname}) - 📅 {u[2]}\n"
                
            msg_text = (
                f"📊 <b>Bot statistikasi:</b>\n\n"
                f"👤 Jami foydalanuvchilar: <b>{total_users} ta</b>\n\n"
                f"🕒 <b>Oxirgi 10 ta foydalanuvchi ro'yxati:</b>\n{user_list}"
            )
            await message.answer(msg_text, parse_mode="HTML")
        except Exception as e:
            await message.answer(f"❌ Statistikada xatolik: {e}")
    else:
        sql.execute("SELECT status, daily_count FROM users WHERE user_id=?", (message.from_user.id,))
        res = sql.fetchone()
        status = res[0] if res else "bepul"
        count = res[1] if res else 0
        limit_val = "Cheksiz" if status == "premium" else f"{count}/3 ta"
        
        await message.answer(
            f"👤 <b>Sizning hisobingiz statusi:</b> {status.upper()}\n"
            f"📈 Bugun yuklangan videolar: {limit_val}"
        )

# =====================================
# ⭐ PREMIUM SOTIB OLISH (TELEGRAM STARS)
# =====================================
@dp.message(F.text == "⭐ Premium sotib olish")
async def send_premium_invoice(message: Message):
    await message.answer(
        "⭐ <b>Premium obuna imkoniyatlari:</b>\n\n"
        "⚡ <b>Tezkor yuklash:</b> Videolar navbatsiz va eng yuqori tezlikda yuklanadi.\n"
        "🚫 <b>Reklamasiz:</b> Videolar ostida bot reklamalari bo'lmaydi.\n"
        "♾️ <b>Cheksiz yuklash:</b> Kunlik 3 ta video cheklovi butunlay o'chadi!",
        parse_mode="HTML"
    )
    
    price = aiogram.types.LabeledPrice(label="Premium 1 oy", amount=50)
    
    await message.answer_invoice(
        title="Premium obuna",
        description="Tezkor tezlik va reklamalarsiz cheksiz yuklash.",
        payload="premium_30_days",
        provider_token="",  
        currency="XTR",     
        prices=[price]
    )

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: aiogram.types.PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def success_payment_handler(message: Message):
    if message.successful_payment.invoice_payload == "premium_30_days":
        try:
            sql.execute("UPDATE users SET status='premium' WHERE user_id=?", (message.from_user.id,))
            db.commit()
            await message.answer("🎉 <b>Tabriklaymiz! Premium status muvaffaqiyatli faollashtirildi!</b>", parse_mode="HTML")
        except Exception as e:
            await message.answer(f"❌ Xatolik yuz berdi: {e}")

# =====================================
# 3. LINK KELGANDA
# =====================================
@dp.message(F.text.contains("instagram.com"))
async def handle_link(message: Message):
    user_id = message.from_user.id
    current_time = get_uzb_time(with_seconds=True)
    user_name = message.from_user.full_name
    username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
    
    allowed, status = check_and_update_limit(user_id)
    is_premium = (status == "premium")
    
    if not allowed:
        await message.answer("❌ <b>Kunlik tekin yuklash limitingiz (3 ta) tugadi!</b>\n\nCheksiz foydalanish uchun Premium xizmatini faollashtiring:", parse_mode="HTML")
        await send_premium_invoice(message)
        return
    
    if message.from_user.id != ADMIN_ID:
        report_msg = (
            f"📥 <b>Botdan foydalanildi!</b> ({status.upper()})\n\n"
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
        if not is_premium:
            await asyncio.sleep(3)
            
        loop = asyncio.get_event_loop()
        path = await loop.run_in_executor(None, download_insta, message.text)
        await msg.edit_text("✅ Yuklandi! Yuborilmoqda...")
        await send_file(message.chat.id, path, is_premium=is_premium)
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
    asyncio.run(main())
