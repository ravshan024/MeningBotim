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
    # Eng sodda salomlashish
    await message.reply("👋 **Instagram yuklovchi botga xush kelibsiz!**\n\nLinkni yuboring, men uni darhol tayyorlab beraman.")

@dp.message(F.text.contains("instagram.com"))
async def handle_link(message: Message):
    user_id = message.from_user.id
    user_data[user_id] = message.text
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Yuklab olish", callback_data="download_insta")]
    ])
    await message.reply("✅ **Havola qabul qilindi.**", reply_markup=keyboard)

@dp.callback_query(F.data == "download_insta")
async def download_insta(callback: CallbackQuery):
    user_id = callback.from_user.id
    url = user_data.get(user_id)
    
    if not url:
        return await callback.answer("❌ Xatolik yuz berdi.")

    # Javobni tozalash
    await callback.message.edit_text("⏳ **Yuklanmoqda...**")
    
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
                await callback.message.answer_photo(photo=status_file)
            else:
                await callback.message.answer_video(video=status_file)
            
            await callback.message.delete()
        else:
            await callback.message.edit_text("❌ **Yuklab bo'lmadi.** Profil yopiq bo'lishi mumkin.")
    
    except Exception:
        await callback.message.edit_text("❌ **Xatolik yuz berdi.**")
    finally:
        for f in os.listdir('.'):
            if f.startswith(unique_name):
                try: os.remove(f)
                except: pass

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
