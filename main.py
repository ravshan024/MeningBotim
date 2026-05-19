import os
import asyncio
import uuid
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
import yt_dlp
from aiohttp import web

logging.basicConfig(level=logging.INFO)

# Tokeningizni shu yerga qo'ying
TOKEN = "8926119680:AAELFYwSVdryZ9Uhpn4ikLV6I2qBJDzQsTE"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_data = {}

@dp.message(F.text == "/start")
async def send_welcome(message: Message):
    # Professional va aniq salomlashish xabari
    await message.reply(
        "👋 **Instagram Media Downloader**\n\n"
        "Men Instagram'dan:\n"
        "🎥 **Reels va Videolar**\n"
        "📸 **Rasmlar**\n"
        "📜 **Stories**\n"
        "yuklab berishga ixtisoslashgan botman.\n\n"
        "👉 **Ishni boshlash uchun shunchaki Instagram havolasini yuboring!**"
    )

@dp.message(F.text.contains("instagram.com"))
async def handle_link(message: Message):
    user_id = message.from_user.id
    user_data[user_id] = message.text
    
    # Tugma bilan ixcham javob
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Yuklab olishni boshlash", callback_data="download_insta")]
    ])
    await message.reply("✅ **Havola qabul qilindi.**\nMedia faylni tayyorlash uchun quyidagi tugmani bosing:", reply_markup=keyboard)

@dp.callback_query(F.data == "download_insta")
async def download_insta(callback: CallbackQuery):
    user_id = callback.from_user.id
    url = user_data.get(user_id)
    
    if not url:
        return await callback.answer("❌ Havola topilmadi, qaytadan yuboring.")

    await callback.message.edit_text("⏳ **Server faylni tayyorlamoqda...**")
    
    unique_name = f"media_{uuid.uuid4().hex}"
    ydl_opts = {
        'format': 'best',
        'outtmpl': f"{unique_name}.%(ext)s",
        'quiet': True,
    }

    try:
        loop = asyncio.get_event_loop()
        def run_dl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        await loop.run_in_executor(None, run_dl)

        actual_file = next((f for f in os.listdir('.') if f.startswith(unique_name)), None)
        
        if actual_file:
            status_file = FSInputFile(actual_file)
            ext = os.path.splitext(actual_file)[1].lower()
            
            if ext in ['.jpg', '.jpeg', '.png']:
                await callback.message.answer_photo(photo=status_file, caption="✅ **Rasm tayyor!**")
            else:
                await callback.message.answer_video(video=status_file, caption="✅ **Video tayyor!**")
            
            await callback.message.delete()
        else:
            await callback.message.edit_text("❌ **Yuklab bo'lmadi.** Profil yopiq (private) bo'lishi mumkin.")
    
    except Exception:
        await callback.message.edit_text("❌ **Xatolik yuz berdi.**")
    finally:
        for f in os.listdir('.'):
            if f.startswith(unique_name):
                try: os.remove(f)
                except: pass

@dp.message(F.text & ~F.text.startswith("/"))
async def alert_message(message: Message):
    # Agar foydalanuvchi link yubormasa, bot uni yo'naltiradi
    await message.reply("⚠️ **Iltimos, Instagram'dan havola (link) yuboring.**\nMen faqat Instagram kontentini yuklay olaman.")

# Server sozlamalari
async def start_server():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is running!"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await start_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
