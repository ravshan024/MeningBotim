import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart
import yt_dlp

BOT_TOKEN = "8926119680:AAELFYwSVdryZ9Uhpn4ikLV6I2qBJDzQsTE"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Instagram link yuboring")


def download_instagram(url):
    ydl_opts = {
        "outtmpl": "%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)

    return file_path


@dp.message(F.text)
async def downloader(message: Message):

    url = message.text

    if "instagram.com" not in url:
        await message.answer("Faqat Instagram link")
        return

    msg = await message.answer("Yuklanmoqda...")

    try:

        loop = asyncio.get_event_loop()

        file_path = await loop.run_in_executor(
            None,
            download_instagram,
            url
        )

        ext = file_path.split(".")[-1].lower()

        if ext == "mp4":
            video = open(file_path, "rb")
            await message.answer_video(video)
            video.close()

        else:
            photo = open(file_path, "rb")
            await message.answer_photo(photo)
            photo.close()

        os.remove(file_path)

        await msg.delete()

    except Exception as e:
        await msg.edit_text(str(e))


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
