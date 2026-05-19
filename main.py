import os
import asyncio
import uuid
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
import yt_dlp
from aiohttp import web

# Tizim loglarini kuzatish
logging.basicConfig(level=logging.INFO)

TOKEN = "8926119680:AAE1HqDgN42U1439hPw1iozphZuQcymEKcs"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Foydalanuvchi ma'lumotlarini vaqtinchalik saqlash xotirasi
user_storage = {}

# 1. /start buyrug'i
@dp.message(F.text == "/start")
async def send_welcome(message: Message):
    await message.reply(
        "👋 **Assalomu alaykum! Sifatli yuklovchi botga xush kelibsiz!**\n\n"
        "🚀 **Bot imkoniyatlari:**\n"
        "📂 **Havola orqali:** YouTube yoki Instagram linkini tashlang, video (MP4) yoki audio yuklab oling.\n"
        "🎵 **Matn orqali:** Istalgan qo'shiq yoki xonanda nomini yozing, men uni qidirib topaman!"
    )

# 2. Havolalarni aniqlash (YouTube va Instagram linklari uchun xatosiz filtr)
@dp.message(F.text.startswith("http://") | F.text.startswith("https://"))
async def process_link(message: Message):
    url = message.text
    user_id = message.from_user.id
    user_storage[user_id] = {"url": url, "is_search": False}
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Sifatli Video (MP4)", callback_data="get_video"),
            InlineKeyboardButton(text="🎵 Tiniq Audio", callback_data="get_audio")
        ]
    ])
    await message.reply("🎬 **Havola qabul qilindi.** Qaysi formatda yuklamoqchisiz?", reply_markup=keyboard)

# 3. Matnli qidiruv (Faqat qo'shiq nomi yozilganda ishlaydi)
@dp.message(F.text & ~F.text.startswith("/"))
async def process_search(message: Message):
    search_text = message.text
    user_id = message.from_user.id
    user_storage[user_id] = {"url": f"ytsearch1:{search_text}", "is_search": True}
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📥 Musiqani yuklash", callback_data="get_audio")
        ]
    ])
    await message.reply(
        f"🔍 **\"{search_text}\"** bo'yicha eng yaxshi variant qidirilmoqda...\n"
        f"Yuklab olish uchun tugmani bosing:", 
        reply_markup=keyboard
    )

# 4. Yuklash va qayta ishlash markazi
@dp.callback_query(F.data.in_(["get_video", "get_audio"]))
async def download_media(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = user_storage.get(user_id)
    
    if not data:
        await callback.answer("❌ Seans muddati tugadi. Qayta yuboring.", show_alert=True)
        return
        
    await callback.message.edit_text("⏳ **Jarayon boshlandi...** Server faylni tayyorlamoqda, iltimos kuting...")
    
    task_type = callback.data
    url = data["url"]
    unique_name = f"media_{uuid.uuid4().hex}"
    
    if task_type == "get_video":
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # Render bepul rejasida eng barqaror format
            'outtmpl': f"{unique_name}.mp4",
            'quiet': True,
            'no_warnings': True,
        }
        output_file = f"{unique_name}.mp4"
    else:
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',  # FFmpeg talab qilmaydigan eng toza format
            'outtmpl': f"{unique_name}.%(ext)s",
            'quiet': True,
            'no_warnings': True,
        }
        output_file = f"{unique_name}.m4a"

    try:
        loop = asyncio.get_event_loop()
        def run_dl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
        await loop.run_in_executor(None, run_dl)
        
        actual_file = output_file
        if task_type == "get_audio" and not os.path.exists(actual_file):
            for f in os.listdir('.'):
                if unique_name in f:
                    actual_file = f
                    break

        if os.path.exists(actual_file):
            await callback.message.edit_text("🚀 **Fayl muvaffaqiyatli yuklandi!** Telegramga yuborilmoqda...")
            status_file = FSInputFile(actual_file)
            
            if task_type == "get_video":
                await callback.message.answer_video(video=status_file, caption="🎬 **Videongiz tayyor!**")
            else:
                caption_text = "🎵 **Qo'shiq nomi bo'yicha topildi!**" if data["is_search"] else "🎵 **Audiongiz tayyor!**"
                await callback.message.answer_audio(audio=status_file, caption=caption_text)
                
            await callback.message.delete()
        else:
            raise FileNotFoundError()
            
    except Exception as e:
        logging.error(f"Yuklashda xato yuz berdi: {e}")
        await callback.message.edit_text(
            "❌ **Yuklashda xatolik yuz berdi!**\n"
            "• Havola noto'g'ri bo'lishi mumkin.\n"
            "• Yoki fayl hajmi juda katta (50MB+)."
        )
    finally:
        # Server to'lib qolmasligi uchun keshni tozalash
        for f in os.listdir('.'):
            if unique_name in f:
                try: os.remove(f)
                except: pass

# Render serverining "Port Scan" xatosini davolash (Soxta veb-sahifa)
async def handle(request):
    return web.Response(text="Bot is running smoothly!")

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
