import os
import sqlite3
import asyncio
import logging
from datetime import datetime
from pathlib import Path

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
import instagrapi

# =====================================
# CONFIG
# =====================================

BOT_TOKEN = os.environ.get("8926119680:AAFrKDnlW8Fbe1IXoKESl1CTN8_QbxPDjIE")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6489364078"))
DOWNLOADS_DIR = "downloads"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
CLEANUP_INTERVAL = 300  # 5 minutes

os.makedirs(DOWNLOADS_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =====================================
# DATABASE
# =====================================

def init_db():
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
    return db, sql

db, sql = init_db()

# =====================================
# SAVE USER
# =====================================

def save_user(user):
    try:
        sql.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
        exists = sql.fetchone()
        
        if exists is None:
            join_date = datetime.now().strftime("%d.%m.%Y %H:%M")
            sql.execute(
                "INSERT INTO users (user_id, full_name, username, join_date) VALUES (?, ?, ?, ?)",
                (user.id, user.full_name, user.username or "N/A", join_date)
            )
            db.commit()
    except Exception as e:
        logger.error(f"Error saving user: {e}")

# =====================================
# FILE CLEANUP
# =====================================

def cleanup_old_files():
    """Eski fayllarni o'chirib tashlash"""
    try:
        current_time = datetime.now().timestamp()
        for filename in os.listdir(DOWNLOADS_DIR):
            filepath = os.path.join(DOWNLOADS_DIR, filename)
            if os.path.isfile(filepath):
                file_time = os.path.getctime(filepath)
                if current_time - file_time > CLEANUP_INTERVAL:
                    os.remove(filepath)
                    logger.info(f"Cleaned up: {filename}")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

# =====================================
# INSTAGRAM DOWNLOADER
# =====================================

def download_instagram_media(url: str) -> dict:
    """Instagram media yuklash"""
    try:
        # instagrapi Client
        cl = instagrapi.Client()
        
        # URL tipini aniqlash
        media_pk = None
        
        if "/reel/" in url:
            media_pk = cl.media_pk_from_url(url)
            media = cl.media_info(media_pk)
            
            video_path = os.path.join(DOWNLOADS_DIR, f"reel_{media_pk}.mp4")
            cl.video_download(media_pk, video_path)
            
            return {"type": "video", "path": video_path, "size": os.path.getsize(video_path)}
        
        elif "/p/" in url:
            media_pk = cl.media_pk_from_url(url)
            media = cl.media_info(media_pk)
            
            if media.media_type == 8:  # Carousel
                paths = []
                for i, item in enumerate(media.resources):
                    if item.media_type == 2:  # Video
                        path = os.path.join(DOWNLOADS_DIR, f"carousel_{media_pk}_{i}.mp4")
                        cl.video_download(media_pk, path)
                    else:  # Photo
                        path = os.path.join(DOWNLOADS_DIR, f"carousel_{media_pk}_{i}.jpg")
                        cl.photo_download(media_pk, path)
                    paths.append(path)
                return {"type": "carousel", "paths": paths}
            
            elif media.media_type == 2:  # Video
                video_path = os.path.join(DOWNLOADS_DIR, f"video_{media_pk}.mp4")
                cl.video_download(media_pk, video_path)
                return {"type": "video", "path": video_path, "size": os.path.getsize(video_path)}
            
            else:  # Photo
                photo_path = os.path.join(DOWNLOADS_DIR, f"photo_{media_pk}.jpg")
                cl.photo_download(media_pk, photo_path)
                return {"type": "photo", "path": photo_path, "size": os.path.getsize(photo_path)}
        
        elif "/stories/" in url:
            user_id = cl.user_id_from_url(url)
            stories = cl.user_stories(user_id)
            
            if stories:
                story = stories[0]
                if story.media_type == 2:  # Video
                    path = os.path.join(DOWNLOADS_DIR, f"story_{user_id}.mp4")
                    cl.story_download(story.pk, user_id, path)
                    return {"type": "video", "path": path, "size": os.path.getsize(path)}
                else:  # Photo
                    path = os.path.join(DOWNLOADS_DIR, f"story_{user_id}.jpg")
                    cl.story_download(story.pk, user_id, path)
                    return {"type": "photo", "path": path, "size": os.path.getsize(path)}
        
        return {"error": "Noma'lum media turi"}
    
    except Exception as e:
        logger.error(f"Download error: {e}")
        return {"error": str(e)}

# =====================================
# MENU
# =====================================

def get_menu(user_id):
    keyboard = [
        [KeyboardButton(text="ℹ️ Yordam")],
        [KeyboardButton(text="🔄 Yangilash")]
    ]
    
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton(text="📊 Statistika")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
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
🔥 Instagram Downloader Bot

✅ Reels
✅ Post (Rasm/Video)
✅ Stories
✅ Carousel (Albom)

📥 Instagram linkini yubor!

Misol:
https://www.instagram.com/reel/ABC123/
https://www.instagram.com/p/XYZ789/
""",
        reply_markup=get_menu(message.from_user.id)
    )

# =====================================
# HELP
# =====================================

@dp.message(F.text == "ℹ️ Yordam")
async def help_cmd(message: Message):
    await message.answer(
        """
📌 Qo'llanma:

1️⃣ Instagram linkini ko'chir
2️⃣ Botga yubor
3️⃣ Formatni tanlang
4️⃣ Faylni yuklang

🔗 Qabul qilinadigan linklar:
• Reels: instagram.com/reel/...
• Posts: instagram.com/p/...
• Stories: instagram.com/stories/...

⚠️ E'tibor: 50MB dan katta fayllar yuborilmaydi
"""
    )

# =====================================
# REFRESH
# =====================================

@dp.message(F.text == "🔄 Yangilash")
async def refresh(message: Message):
    cleanup_old_files()
    await message.answer("✅ Keshlash tozalandi")

# =====================================
# STATS
# =====================================

@dp.message(F.text == "📊 Statistika")
async def stats_button(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    sql.execute("SELECT * FROM users")
    users = sql.fetchall()
    
    text = f"👥 Jami foydalanuvchilar: {len(users)}\n\n"
    text += "📋 Oxirgi 10 ta foydalanuvchi:\n\n"
    
    for user in users[-10:]:
        text += f"👤 {user[1]}\n📛 @{user[2]}\n🕒 {user[3]}\n🆔 {user[0]}\n\n"
    
    await message.answer(text)

# =====================================
# INSTAGRAM LINK HANDLER
# =====================================

@dp.message(F.text.contains("instagram.com"))
async def handle_instagram_link(message: Message):
    url = message.text.strip()
    
    buttons = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📥 Yuklash", callback_data=f"download|{url}")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
        ]
    )
    
    await message.answer(
        "🔍 Media topildi\n📥 Yuklamoqchimisiz?",
        reply_markup=buttons
    )

# =====================================
# CALLBACKS
# =====================================

@dp.callback_query(F.data == "cancel")
async def cancel_download(call: CallbackQuery):
    await call.message.delete()
    await call.answer("Bekor qilindi")

@dp.callback_query(F.data.startswith("download|"))
async def download_media(call: CallbackQuery):
    url = call.data.replace("download|", "")
    
    await call.message.edit_text("⏳ Yuklanmoqda... Kuting")
    
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, download_instagram_media, url)
        
        if "error" in result:
            await call.message.edit_text(f"❌ Xato: {result['error']}")
            return
        
        # File size tekshirish
        if result["type"] == "video" and result["size"] > MAX_FILE_SIZE:
            await call.message.edit_text("❌ Fayl juda katta (50MB dan ko'p)")
            if os.path.exists(result["path"]):
                os.remove(result["path"])
            return
        
        # Faylni yuborish
        if result["type"] == "video":
            await call.message.answer_video(FSInputFile(result["path"]))
        elif result["type"] == "photo":
            await call.message.answer_photo(FSInputFile(result["path"]))
        elif result["type"] == "carousel":
            for path in result["paths"]:
                if path.endswith(".mp4"):
                    await call.message.answer_video(FSInputFile(path))
                else:
                    await call.message.answer_photo(FSInputFile(path))
        
        # Fayllarni o'chirib tashlash
        if result["type"] == "carousel":
            for path in result["paths"]:
                if os.path.exists(path):
                    os.remove(path)
        else:
            if os.path.exists(result["path"]):
                os.remove(result["path"])
        
        await call.message.edit_text("✅ Yuklab olindi!")
    
    except Exception as e:
        logger.error(f"Download error: {e}")
        await call.message.edit_text(f"❌ Xato:\n{str(e)[:100]}")

# =====================================
# CLEANUP TASK
# =====================================

async def cleanup_task():
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        cleanup_old_files()

# =====================================
# MAIN
# =====================================

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Cleanup task ishini boshlash
    asyncio.create_task(cleanup_task())
    
    logger.info("Bot ishlashni boshladı...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
