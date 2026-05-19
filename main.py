import os
import asyncio
import uuid
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile

# Render xatoliklarini kuzatish uchun log tizimi
logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Foydalanuvchi ma'lumotlarini vaqtinchalik xotirada saqlash
user_storage = {}

@dp.message(F.text.startswith("http") | F.text.startswith("https"))
async def process_link(message: Message):
    url = message.text
    user_id = message.from_user.id
    user_storage[user_id] = url
    
    # Qulay va chiroyli tugmalar paneli
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
        
    await callback.message.edit_text("⏳ Jarayon boshlandi... Fayl qayta ishlanmoqda...")
    
    task_type = callback.data
    unique_name = f"media_{uuid.uuid4().hex}"
    
    # yt-dlp uchun maxsus sozlamalar
    if task_type == "get_video":
        ydl_opts = {
            # 1080p gacha bo'lgan eng yaxshi video va audioni birlashtirish
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': f"{unique_name}.mp4",
            'quiet': True,
            'no_warnings': True,
            # Instagram va ijtimoiy tarmoq yozuvlari va metama'lumotlarini tozalash
            'postprocessor_args': ['-metadata', 'comment=', '-metadata', 'title=', '-metadata', 'author=', '-metadata', 'description='],
        }
        output_file = f"{unique_name}.mp4"
    else:
        # Haqiqiy tiniq 320kbps MP3 ajratish sozlamasi
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
        # 10-15 kishi ishlatsa bot qotib qolmasligi uchun yuklash jarayonini asinxron bajarish
        import yt_dlp
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
            raise FileNotFoundError("Fayl yuklanmadi")
            
    except Exception as e:
        logging.error(f"Yuklash xatosi: {e}")
        await callback.message.edit_text(
            "❌ Yuklashda xatolik yuz berdi.\n"
            "Sababi: Havola xato yoki video hajmi juda katta (50MB+ dan yuqori)."
        )
    finally:
        # Server to'lib qolib, bot mutlaqo to'xtab qolmasligi uchun keshni tozalash
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except:
                pass
        # Qo'shimcha vaqtinchalik m4a yoki qoldiq fayllarni tozalash
        for f in os.listdir('.'):
            if unique_name in f:
                try: os.remove(f)
                except: pass

async def main():
    # Kodingizning tepa qismlari o'zgarishsiz qoladi...

async def main():
    # Render port scan xatosini to'g'rilash uchun soxta port ochamiz
    import asyncio
    from aiohttp import web
    
    async def handle(request):
        return web.Response(text="Bot is running!")
        
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render yuboradigan portni o'qiydi yoki avtomatik 10000-portda ishlaydi
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 10000)))
    await site.start()
    
    # Telegram botni ishga tushirish
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run
