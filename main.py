TOKEN = os.environ.get("8926119680:AAE1HqDgN42Ul439hPw1iozphZuQcymEKcs")
import os
import asyncio
import uuid
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
import yt_dlp
from aiohttp import web

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

user_storage = {}

# 1. Agar foydalanuvchi havola (link) yuborsa
@dp.message(F.text.startswith("http") | F.text.startswith("https"))
async def process_link(message: Message):
    url = message.text
    user_id = message.from_user.id
    user_storage[user_id] = {"url": url, "is_search": False}
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Sifatli Video (MP4)", callback_data="get_video"),
            InlineKeyboardButton(text="🎵 Tiniq MP3 Audio", callback_data="get_audio")
        ]
    ])
    await message.reply("🎬 Havola aniqlandi. Formatni tanlang:", reply_markup=keyboard)

# 2. Agar foydalanuvchi qo'shiq nomi yoki xonandani yozsa (Matnli qidiruv)
@dp.message(F.text)
async def process_search(message: Message):
    search_text = message.text
    user_id = message.from_user.id
    # YouTube qidiruv formati: ytsearch1: so'z
    user_storage[user_id] = {"url": f"ytsearch1:{search_text}", "is_search": True}
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎵 Musiqani yuklash (MP3)", callback_data="get_audio")
        ]
    ])
    await message.reply(
        f"🔍 \"{search_text}\" bo'yicha eng yaxshi musiqani topishga tayyorman.\n"
        f"Yuklash uchun pastdagi tugmani bosing:", 
        reply_markup=keyboard
    )

@dp.callback_query(F.data.in_(["get_video", "get_audio"]))
async def download_media(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = user_storage.get(user_id)
    
    if not data:
        await callback.answer("Ma'lumot topilmadi. Qayta yozing.", show_alert=True)
        return
        
    await callback.message.edit_text("⏳ So'rovingiz bajarilmoqda... Server qidirmoqda va yuklamoqda...")
    
    task_type = callback.data
    url = data["url"]
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
                'preferredquality': '320', # Eng tiniq 320kbps format
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
            await callback.message.edit_text("🚀 Fayl tayyor! Telegramga yuborilmoqda...")
            status_file = FSInputFile(output_file)
            
            if task_type == "get_video":
                await callback.message.answer_video(video=status_file, caption="🎬 Videongiz tayyor!")
            else:
                caption_text = "🎵 Qo'shiq nomi bo'yicha qidirib topildi!" if data["is_search"] else "🎵 Videodan MP3 ajratib olindi!"
                await callback.message.answer_audio(audio=status_file, caption=caption_text)
                
            await callback.message.delete()
        else:
            raise FileNotFoundError()
            
    except Exception as e:
        await callback.message.edit_text("❌ Xatolik! Bunday nomdagi musiqa topilmadi yoki juda katta (50MB+).")
    finally:
        # Server to'lib qolmasligi uchun keshni tozalash
        if os.path.exists(output_file):
            try: os.remove(output_file)
            except: pass
        for f in os.listdir('.'):
            if unique_name in f:
                try: os.remove(f)
                except: pass

# Render bepul rejadagi port scan xatosini davolash
async def handle(request):
    return web.Response(text="Bot is active!")

async def main():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
