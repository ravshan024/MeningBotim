import os
import asyncio
import uuid
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.types import FSInputFile
import yt_dlp

TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(F.text.startswith("http"))
async def handle_link(message: Message):
    url = message.text
    await message.answer("🔄 Video yuklanmoqda, iltimos kuting...")
    
    # Har bir video uchun takrorlanmas nom yaratamiz
    file_name = f"video_{uuid.uuid4().hex}.mp4"
    
    try:
        ydl_opts = {
            'format': 'best',
            'outtmpl': file_name,
            'quiet': True,  # Render qotib qolmasligi uchun ortiqcha yozuvlarni oʻchiramiz
            'no_warnings': True,
        }
        
        # Yuklash jarayonini serverni qotirmasdan bajarish
        loop = asyncio.get_event_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
        await loop.run_in_executor(None, download)
        
        # Videoni xavfsiz usulda yuborish
        video_file = FSInputFile(file_name)
        await message.answer_video(video=video_file, caption="✨ Video muvaffaqiyatli yuklandi!")
        
    except Exception as e:
        await message.answer("❌ Yuklashda xatolik bo'ldi. Havola noto'g'ri yoki bu videoni yuklab bo'lmaydi.")
        
    finally:
        # Har qanday holatda ham server toʻlib qolmasligi uchun faylni oʻchiramiz
        if os.path.exists(file_name):
            os.remove(file_name)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
