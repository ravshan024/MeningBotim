import os
import asyncio
import uuid
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
import yt_dlp
from aiohttp import web

logging.basicConfig(level=logging.INFO)

TOKEN = "8926119680:AAE1HqDgN42U1439hPw1iozphZuQcymEKcs"
bot = Bot(token=TOKEN)
dp = Dispatcher()

user_storage = {}

# 1. /start buyrug'i uchun maxsus qism (Musiqa deb o'ylab ketmasligi uchun)
@dp.message(F.text == "/start")
async def send_welcome(message: Message):
    await message.reply(
        "👋 Salom! Men YouTube va Instagram yuklovchi botman.\n\n"
        "🎯 **Imkoniyatlarim:**\n"
        "• Menga video havolasini (link) yuborsangiz, uni logotiplarsiz video (MP4) yoki MP3 qilib beraman.\n"
        "• Shunchaki qo'shiq yoki xonanda nomini yozsangiz, sizga musiqasini topib beraman!"
    )

# 2. Agar foydalanuvchi havola (Link) yuborsa
@dp.message(F.text.startswith("http://") | F.text.startswith("https://") | F.text.contains("instagram.com") | F.text.contains("youtu"))
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
    await message.reply("🎬 Havola aniqlandi! Quyidagi formatlardan birini tanlang:", reply_markup=keyboard)

# 3. Agar foydalanuvchi oddiy matn yozsa (Qo'shiq qidirish)
@dp.message(F.text & ~F.text.startswith("/"))
async def process_search(message: Message):
    search_text = message.text
    user_id = message.from_user.id
    user_storage[user_id] = {"url": f"ytsearch1:{search_text}", "is_search": True}
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎵 Musiqani yuklash (MP3)", callback_data="get_audio")
        ]
    ])
    await message.reply(
        f"🔍 \"{search_text}\" bo'yicha musiqa qidirilmoqda...\n"
        f"Yuklab olish uchun pastdagi tugmani bosing:", 
        reply_markup=keyboard
    )

@dp.callback_query(F.data.in_(["get_video", "get_audio"]))
async def download_media(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = user_storage.get(user_id)
    
    if not data:
        await callback.answer("Xatolik! Ma'lumot topilmadi. Qayta urinib ko'ring.", show_alert=True)
        return
        
    await callback.message.edit_text("⏳ So'rovingiz bajarilmoqda... Server yuklamoqda, iltimos kuting...")
    
    task_type = callback.data
    url = data["url"]
    unique_name = f"media_{uuid.uuid4().hex}"
    
    if task_type == "get_video":
        ydl_opts = {
            'format': 'best',  # Render bepul rejasida xato bermasligi uchun eng barqaror format
            'outtmpl': f"{unique_name}.mp4",
            'quiet': True,
            'no_warnings': True,
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
            await callback.message.edit_text("🚀 Fayl tayyor! Telegramga yuborilmoqda...")
            status_file = FSInputFile(output_file)
            
            if task_type == "get_video":
                await callback.message.answer_video(video=status_file, caption="🎬 Videongiz tayyor!")
            else:
                caption_text = "🎵 Qo'shiq topildi!" if data["is_search"] else "🎵 Audio ajratib olindi!"
                await callback.message.answer_audio(audio=status_file, caption=caption_text)
                
            await callback.message.delete()
        else:
            raise FileNotFoundError()
            
    except Exception as e:
        logging.error(f"Yuklashda xato: {e}")
        await callback.message.edit_text("❌ Yuklashda xatolik yuz berdi! Havola noto'g'ri yoki fayl hajmi juda katta (50MB+).")
    finally:
        if os.path.exists(output_file):
            try: os.remove(output_file)
            except: pass
        for f in os.listdir('.'):
            if unique_name in f:
                try: os.remove(f)
                except: pass

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
