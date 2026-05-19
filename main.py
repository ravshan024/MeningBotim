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

# ⚠️ BOTFATHER BERGAN ENG OXIRGI YANGI TOKEN
TOKEN = "8926119680:AAELFYwSVdryZ9Uhpn4ikLV6I2qBJDzQsTE"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_storage = {}

@dp.message(F.text == "/start")
async def send_welcome(message: Message):
    await message.reply(
        "✨ **Professional va Aqlli yuklovchi botga xush kelibsiz!**\n\n"
        "🚀 **Bot nimalarni yuklay oladi:**\n"
        "📸 **Instagram:** Reels, Video, Rasm (Post) va Stories (Hikoyalar) - Maksimal sifatda!\n"
        "🎬 **YouTube:** Shorts va istalgan hajmdagi videolar - Avtomatik siqish tizimi bilan!\n\n"
        "👉 Menga shunchaki havola (link) yuboring:"
    )

# Havolalarni tutib olish filtri
@dp.message(F.text.startswith("http://") | F.text.startswith("https://") | F.text.contains("youtu") | F.text.contains("instagram"))
async def process_link(message: Message):
    url = message.text
    user_id = message.from_user.id
    user_storage[user_id] = {"url": url}
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Sifatli Media (MP4 / JPG)", callback_data="get_video"),
            InlineKeyboardButton(text="🎵 Faqat Audio (MP3)", callback_data="get_audio")
        ]
    ])
    await message.reply("⚡ **Havola tekshirildi.** Yuklash turini tanlang:", reply_markup=keyboard)

@dp.message(F.text & ~F.text.startswith("/"))
async def no_text_alert(message: Message):
    await message.reply("⚠️ **Iltimos, botga faqat havola yuboring!**\nInstagram yoki YouTube linklarini kutaman.")

# Fonda ishlaydigan mukammal yuklash tizimi
async def background_download(callback: CallbackQuery, task_type: str, url: str):
    unique_name = f"media_{uuid.uuid4().hex}"
    is_instagram = "instagram.com" in url.lower()
    
    # Professional tarmoq va brauzer imitatsiya sozlamalari (Bloklanishdan himoya)
    common_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        'extractor_args': {
            'instagram': {'max_comments': 0},
            'youtube': {'player_client': ['android', 'web']}
        }
    }

    if task_type == "get_video":
        if is_instagram:
            # Instagram uchun original eng yuqori sifat (Rasm yoki Video farqi yo'q)
            ydl_opts = {
                **common_opts,
                'format': 'best',
                'outtmpl': f"{unique_name}.%(ext)s",
            }
        else:
            # YouTube uchun aqlli tekin server sozlamasi: 50MB dan oshmaydigan eng yaxshi formatni tanlaydi
            ydl_opts = {
                **common_opts,
                'format': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]/best',
                'max_filesize': 49 * 1024 * 1024, # 49MB xavfsizlik chegarasi
                'outtmpl': f"{unique_name}.mp4",
            }
    else:
        # Audio (MP3) yuklash sozlamasi
        ydl_opts = {
            **common_opts,
            'format': 'ba/b',
            'outtmpl': f"{unique_name}.%(ext)s",
        }

    try:
        loop = asyncio.get_event_loop()
        def run_dl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
        await loop.run_in_executor(None, run_dl)
        
        # Yuklangan faylni kengaytmasini aniqlash (Rasm, Video yoki Audio)
        actual_file = None
        for f in os.listdir('.'):
            if f.startswith(unique_name):
                actual_file = f
                break

        if actual_file and os.path.exists(actual_file):
            ext = os.path.splitext(actual_file)[1].lower()
            status_file = FSInputFile(actual_file)
            
            await callback.message.answer("🚀 **Fayl muvaffaqiyatli tayyorlandi!** Telegramga yuborilmoqda...")
            
            # Fayl turiga qarab professional formatda yuborish
            if task_type == "get_video":
                if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    await callback.message.answer_photo(photo=status_file, caption="📸 **Instagram’dan yuqori sifatli rasm!**")
                else:
                    await callback.message.answer_video(video=status_file, caption="🎬 **Siz so'ragan video tayyor!**")
            else:
                await callback.message.answer_audio(audio=status_file, caption="🎵 **Musiqa formatidagi audio tayyor!**")
                
            try: await callback.message.delete()
            except: pass
        else:
            raise FileNotFoundError()
            
    except Exception as e:
        logging.error(f"Yuklashda xato yuz berdi: {e}")
        await callback.message.answer(
            "❌ **Yuklab bo'lmadi!**\n\n"
            "• Havola noto'g'ri yoki Story (Hikoya) muddati tugab bo'lgan (yopiq profil).\n"
            "• Yoki ushbu YouTube video siqilgan holatda ham 50 MB dan oshib ketdi."
        )
    finally:
        # Server xotirasini toza tutish (Render diskini tozalash)
        for f in os.listdir('.'):
            if f.startswith(unique_name):
                try: os.remove(f)
                except: pass

@dp.callback_query(F.data.in_(["get_video", "get_audio"]))
async def handle_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = user_storage.get(user_id)
    
    if not data:
        await callback.answer("❌ Seans muddati tugadi. Havolani qayta yuboring.", show_alert=True)
        return
        
    await callback.answer("⏳ Yuklash jarayoni boshlandi...")
    await callback.message.edit_text("⏳ **Tizim ishlamoqda...** Havoladagi media tahlil qilinmoqda va yuklanmoqda...")
    
    # Render qotib qolmasligi uchun yuklashni fonda (Background task) bajarish
    asyncio.create_task(background_download(callback, callback.data, data["url"]))

async def handle_ping(request):
    return web.Response(text="Bot is running completely online!")

async def start_web_server():
    app = web.Application()
    app.router.add_route('*', '/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
