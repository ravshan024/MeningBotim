import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
import yt_dlp

TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(F.text.startswith("http"))
async def handle_link(message: Message):
    url = message.text
    await message.answer("🔄 Video yuklanmoqda, kuting...")
    try:
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'video.mp4',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        await message.answer_video(video=open("video.mp4", "rb"))
        os.remove("video.mp4")
    except Exception as e:
        await message.answer("❌ Yuklashda xatolik bo'ldi yoki havola noto'g'ri.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
