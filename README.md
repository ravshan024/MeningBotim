# 📥 Instagram Downloader Bot

Instagram Reels, Post, Video va rasmlarni yuklab oluvchi Telegram bot.

---

## 🚀 Ishga tushirish

### 1. O'rnatish

```bash
pip install -r requirements.txt
```

### 2. Muhit o'zgaruvchilarini sozlash

**.env fayl yoki terminal orqali:**

```bash
export BOT_TOKEN="TOKEN_BU_YERGA"   # haqiqiy tokenni yozing
export ADMIN_ID="SIZNING_ID"        # Telegram ID ingiz
```

> ⚠️ **BOT_TOKEN ni hech qachon README yoki GitHub ga yozmang!**
> Token ochiq bo'lsa [@BotFather](https://t.me/BotFather) da yangi token oling.

### 3. Ishga tushirish

```bash
python main.py
```

---

## ⚙️ Render.com ga deploy qilish

1. Render.com → **New Web Service**
2. GitHub repo ni ulang
3. **Environment** bo'limiga qo'shing:

| Key | Value |
|-----|-------|
| `BOT_TOKEN` | BotFather dan olgan token |
| `ADMIN_ID` | Telegram ID ingiz |

4. **Start Command:** `python main.py`

---

## 🔑 Xususiyatlar

| Xususiyat | Tavsif |
|-----------|--------|
| yt-dlp | Instagram media yuklash |
| Reels & Post | Video va rasm yuklash |
| MP3 | Audio yuklash |
| Admin panel | Foydalanuvchi statistikasi |
| Broadcast | Barcha foydalanuvchilarga xabar |
| Render ready | Web server o'rnatilgan |

---

## 📦 Kerakli kutubxonalar

```
aiogram==3.7.0
aiohttp==3.9.5
yt-dlp
```

---

## 🛠️ Admin buyruqlari

| Buyruq | Tavsif |
|--------|--------|
| `/stats` | Foydalanuvchilar statistikasi |
| `/broadcast <xabar>` | Hammaga xabar yuborish |

---

## ⚠️ Eslatma

Instagram ba'zan yuklab olishni cheklaydi.
Xato bo'lsa, biroz kutib qayta urining.
