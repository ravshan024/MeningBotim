import os
import asyncio
import uuid
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
import yt_dlp

# Loglarni yoqamiz
logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Vaqtinchalik xotira
user_storage = {}

@dp.message(F.text.startswith("http") | F.text.startswith("https"))
async def process_link(message: Message):
    url = message.text
    user_id = message.from_user.id
    user_storage[user_id] = url
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Sifatli Video (MP4)", callback_data="get_video"),
            InlineKeyboardButton(text="🎵 Tiniq MP3 Audio", callback_data="get_audio")
        ]
    ])
    await message.reply("Formatni tanlang:", reply_markup=keyboard)

@dp.callback_query(F.data.in_(["get_video", "get_audio"]))
async def download_media(callback: CallbackQuery):
    user_id = callback.from_user.id
    url = user_storage.get(user_id)
    
    if not url:
        await callback.answer("Havola topilmadi. Linkni qayta yuboring.", show_alert=True)
        return
        
    await callback.message.edit_text("⏳ Jarayon boshlandi... Fayl yuklanmoqda...")
    
    task_type = callback.data
    unique_name = f"media_{uuid.uuid4().hex}"
    
    if task_type == "get_video":
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': f"{unique_name}.mp4",
            'quiet': True,
            'no_warnings': True,
            'postprocessor_args': ['-metadata', 'comment=', '-metadata', 'title=', '-metadata', 'author=', '-metadata', 'description='],
        }
        output_file = f"{unique_name}.mp4"
    else:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f"{unique_name}.%(ext)s",
            'quiet': True,
            'no_warnings': True,
            'postpreprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
        }
        output_file = f"{unique_name}.mp3"

    try:
        loop = asyncio.get_event_loop()
        def run_dl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
        await loop.run_in_executor(None, run_dl)
        
        if os.path.exists(output_file):
            await callback.message.edit_text("🚀 Fayl tayyor! Telegramga yuklanmoqda...")
            status_file = FSInputFile(output_file)
            
            if task_type == "get_video":
                await callback.message.answer_video(video=status_file, caption="🎬 Videongiz tayyor!")
            else:
                await callback.message.answer_audio(audio=status_file, caption="🎵 Yuqori sifatli MP3!")
                
            await callback.message.delete()
        else:
            raise FileNotFoundError()
            
    except Exception as e:
        await callback.message.edit_text("❌ Yuklashda xatolik bo'ldi. Havola noto'g'ri yoki video juda og'ir.")
    finally:
        if os.path.exists(output_file):
            try: os.remove(output_file)
            except: pass
        for f in os.listdir('.'):
            if unique_name in f:
                try: os.remove(f)
                except: pass

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
