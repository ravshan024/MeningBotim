import os
import asyncio
import uuid
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
import yt_dlp

# Loglarni yoqamiz (Renderda kuzatish oson bo'lishi uchun)
logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Vaqtinchalik ma'lumotlar ombori
user_data = {}

@dp.message(F.text.startswith("http"))
async def handle_incoming_link(message: Message):
    url = message.text
    user_id = message.from_user.id
    user_data[user_id] = url
    
    # Chiroyli va qulay boshqaruv tugmalari
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 High Video (1080p/Best)", callback_data="video_best"),
            InlineKeyboardButton(text="📱 Medium Video (Telegram Fast)", callback_data="video_medium")
        ],
        [
            InlineKeyboardButton(text="🎵 Tiniq MP3 Audio (320kbps)", callback_data="audio_mp3")
        ]
    ])
    
    await message.reply(
        "✨ Havola qabul qilindi!\n"
        "Iltimos, o'zingizga kerakli formatni tanlang:", 
        reply_markup=buttons
    )

@dp.callback_query(F.data.startswith("video_") | F.data.startswith("audio_"))
async def start_downloading(callback: CallbackQuery):
    user_id = callback.from_user.id
    url = user_data.get(user_id)
    
    if not url:
        await callback.answer("❌ Havola muddati o'tgan. Linkni qayta yuboring.", show_alert=True)
        return
        
    action = callback.data
    await callback.message.edit_text("⏳ So'rovingiz qayta ishlanmoqda... Server yuklamoqda...")
    
    # Unikal fayl nomi yaratish (Kesh aralashib ketmasligi uchun)
    unique_id = uuid.uuid4().hex
    
    try:
        if "video" in action:
            # Instagram yozuvlari va reklamalarni olib tashlash hamda 1080p yuklash sozlamalari
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # Eng yuqori 1080p gacha format
                'outtmpl': f"video_{unique_id}.%(ext)s",
                'quiet': True,
                'no_warnings': True,
                'merge_output_format': 'mp4',
                # Instagram brend belgilarini (watermark) va metadata yozuvlarini tozalash buyruqlari
                'postprocessor_args': ['-metadata', 'comment=', '-metadata', 'title=', '-metadata', 'author='],
                'max_filesize': 48 * 1024 * 1024, # 50MB dan oshsa avtomatik siqadi yoki moslashtiradi
            }
            
            if action == "video_medium":
                # Tezkor yuklanuvchi o'rtacha sifat (Katta 1-2 soatlik videolar uchun xavfsiz format)
                ydl_opts['format'] = 'worstvideo[ext=mp4]+bestaudio[ext=m4a]/worst'
                
            final_ext = "mp4"
            
        elif action == "audio_mp3":
            # Videodan eng yuqori sifatli MP3 ajratib olish (320kbps gacha)
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f"audio_{unique_id}.%(ext)s",
                'quiet': True,
                'no_warnings': True,
                'postpreprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320', # Eng tiniq audio sifati
                }],
            }
            final_ext = "mp3"

        # Yuklash jarayonini Render qotib qolmasligi uchun asinxron bajarish
        loop = asyncio.get_event_loop()
        def download_process():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
        await loop.run_in_executor(None, download_process)
        
        # Tayyor bo'lgan faylni qidirib topish
        downloaded_file = None
        for file in os.listdir('.'):
            if unique_id in file:
                downloaded_file = file
                break
                
        if downloaded_file and os.path.exists(downloaded_file):
            await callback.message.edit_text("🚀 Fayl tayyor! Telegramga yuklanmoqda...")
            media = FSInputFile(downloaded_file)
            
            if "video" in action:
                await callback.message.answer_video(video=media, caption="🎬 @SizningBotigiz orqali yuklab olindi!")
            else:
                await callback.message.answer_audio(audio=media, caption="🎵 Tiniq audio format!")
                
            await callback.message.delete()
        else:
            raise Exception("Fayl topilmadi")
            
    except Exception as e:
        logging.error(f"Xatolik yuz berdi: {str(e)}")
        await callback.message.edit_text(
            "❌ Yuklashda xatolik yuz berdi!\n\n"
            "⚠️ Sababi:\n"
            "1. Havola noto'g'ri bo'lishi mumkin.\n"
            "2. Video hajmi bepul server limitidan (50MB) juda katta. "
            "Katta videolar uchun 'Medium Video' tugmasidan foydalanib ko'ring."
        )
        
    finally:
        # Server ichida axlat fayllar qolib ketib, bot qotib qolmasligi uchun tozalash
        for file in os.listdir('.'):
            if unique_id in file:
                try:
                    os.remove(file)
                except:
                    pass

async def main():
    # Eski xabarlarni tozalab, faqat yangi xabarlarga javob berishni yoqamiz
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
