import os
import asyncio
import uuid
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
import yt_dlp
from aiohttp import web

logging.basicConfig(level=logging.INFO)

TOKEN = "8926119680:AAELFYwSVdryZ9Uhpn4ikLV6I2qBJDzQsTE"
bot = Bot(token=TOKEN)
dp = Dispatcher()

user_storage = {}

@dp.message(F.text == "/start")
async def send_welcome(message: Message):
    await message.reply(
        "👋 **Assalomu alaykum! Professional yuklovchi botga xush kelibsiz!**\n\n"
        "🚀 **Bot imkoniyatlari:**\n"
        "📂 **Havola orqali:** YouTube yoki Instagram linkini tashlang.\n"
        "🎵 **Matn orqali:** Istalgan qo'shiq nomini yozing, men uni topaman!"
    )

@dp.message(F.text.startswith("http://") | F.text.startswith("https://") | F.text.contains("youtu") | F.text.contains("instagram"))
async def process_link(message: Message):
    url = message.text
    user_id = message.from_user.id
    user_storage[user_id] = {"url": url, "is_search": False}
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Sifatli Video (MP4)", callback_data="get_video"),
            InlineKeyboardButton(text="🎵 Tiniq Audio (MP3)", callback_data="get_audio")
        ]
    ])
    await message.reply("🎬 **Havola aniqlandi.** Yuklash formatini tanlang:", reply_markup=keyboard)

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

@dp.callback_query(F.data.in_(["get_video", "get_audio"]))
async def download_media(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = user_storage.get(user_id)
    
    if not data:
        await callback.answer("❌ Seans muddati tugadi. Qayta yuboring.", show_alert=True)
        return
        
    await callback.message.edit_text("⏳ **Jarayon boshlandi...** Server yuklamoqda, iltimos kuting...")
    
    task_type = callback.data
    url = data["url"]
    unique_name = f"media_{uuid.uuid4().hex}"
    
    common_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }

    if task_type == "get_video":
        ydl_opts = {
            **common_opts,
            # FFmpeg (birlashtiruvchi) dasturisiz Renderda silliq ishlashi uchun yaxlit tayyor MP4 format buyrug'i
            'format': 'b[ext=mp4]/b', 
            'outtmpl': f"{unique_name}.mp4",
        }
        output_file = f"{unique_name}.mp4"
    else:
        ydl_opts = {
            **common_opts,
            'format': 'ba/b',
            'outtmpl': f"{unique_name}.%(ext)s",
        }
        output_file = f"{unique_name}.mp3"

    try:
        loop = asyncio.get_event_loop()
        def run_dl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
        await loop.run_in_executor(None, run_dl)
        
        actual_file = output_file
        if not os.path.exists(actual_file):
            for f in os.listdir('.'):
                if unique_name in f:
                    actual_file = f
                    break

        if os.path.exists(actual_file):
            await callback.message.edit_text("🚀 **Fayl tayyor!** Telegramga yuborilmoqda...")
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
        logging.error(f"Yuklashda xato: {e}")
        await callback.message.edit_text(
            "❌ **Yuklashda xatolik yuz berdi!**\n"
            "• Havola noto'g'ri yoki yopiq bo'lishi mumkin.\n"
            "• Yoki video hajmi Telegram limiti (50MB) dan katta."
        )
    finally:
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
