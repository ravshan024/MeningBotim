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
        "👋 **Assalomu alaykum! Sifatli va tezkor yuklovchi botga xush kelibsiz!**\n\n"
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

# Yuklash og'ir jarayon bo'lgani uchun uni Background Task qilib fonda bajaramiz
async def background_download(callback: CallbackQuery, task_type: str, url: str, is_search: bool):
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
            await callback.message.answer(f"🚀 **Fayl yuklab olindi.** Telegramga yuborilmoqda...")
            status_file = FSInputFile(actual_file)
            
            if task_type == "get_video":
                await callback.message.answer_video(video=status_file, caption="🎬 **Videongiz tayyor!**")
            else:
                caption_text = "🎵 **Qo'shiq nomi bo'yicha topildi!**" if is_search else "🎵 **Audiongiz tayyor!**"
                await callback.message.answer_audio(audio=status_file, caption=caption_text)
                
            try: await callback.message.delete()
            except: pass
        else:
            raise FileNotFoundError()
            
    except Exception as e:
        logging.error(f"Yuklashda xato: {e}")
        await callback.message.answer(
            "❌ **Yuklashda xatolik yuz berdi!**\n"
            "• Havola noto'g'ri, yopiq yoki o'chirilgan bo'lishi mumkin.\n"
            "• Yoki fayl hajmi juda katta."
        )
    finally:
        for f in os.listdir('.'):
            if unique_name in f:
                try: os.remove(f)
                except: pass

@dp.callback_query(F.data.in_(["get_video", "get_audio"]))
async def handle_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = user_storage.get(user_id)
    
    if not data:
        await callback.answer("❌ Seans muddati tugadi. Qayta yuboring.", show_alert=True)
        return
        
    # Render kutib qolmasligi uchun darhol Telegram va Renderga "Javob qabul qilindi" signali yuboriladi
    await callback.answer("⏳ Yuklash boshlandi...")
    await callback.message.edit_text("⏳ **Jarayon boshlandi...** Server yuklamoqda, iltimos kuting...")
    
    # Asosiy zanjirni bloklamaslik uchun fonda alohida vazifa (Task) sifatida ishga tushiramiz
    asyncio.create_task(background_download(callback, callback.data, data["url"], data["is_search"]))

async def handle_ping(request):
    return web.Response(text="Server is up and running!")

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
