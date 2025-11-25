import os
import asyncio
import json
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F

# ====== Настройки ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise ValueError("❌ Переменная BOT_TOKEN не задана!")

ADMIN_ID = int(ADMIN_ID) if ADMIN_ID and ADMIN_ID.isdigit() else None

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

WELCOME_FILE = "welcome.json"  # файл для хранения настроек приветствия

# ====== Веб сервер для Render ======
async def handle(request):
    return web.Response(text="Bot is running 🚀")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.getenv("PORT", 8000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Web server running on port {port}")

# ====== Команды приветствия ======
@dp.message(F.text.startswith("+приветствие текст"))
async def set_welcome_text(message: types.Message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return await message.reply("❌ У вас нет прав для изменения приветствия.")
    
    text = message.text[len("+приветствие текст"):].strip()
    if not text:
        return await message.reply("❗ Введите текст приветствия.\nПример: +приветствие текст Привет, {имя}!")
    
    settings = {}
    if os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
    
    settings["text"] = text
    with open(WELCOME_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)
    
    await message.answer("✅ Текст приветствия обновлён!")

@dp.message(F.text.startswith("+приветствие медиа"))
async def set_welcome_media(message: types.Message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return await message.reply("❌ У вас нет прав для изменения приветствия.")
    
    url = message.text[len("+приветствие медиа"):].strip()
    if not url:
        return await message.reply("❗ Укажите URL стикера, GIF или картинки.")
    
    settings = {}
    if os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
    
    settings["media"] = url
    with open(WELCOME_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)
    
    await message.answer("✅ Медиа приветствия обновлено!")

@dp.message(F.text.startswith("+приветствие кнопки"))
async def set_welcome_buttons(message: types.Message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return await message.reply("❌ У вас нет прав для изменения приветствия.")
    
    buttons_text = message.text[len("+приветствие кнопки"):].strip()
    buttons = []
    try:
        for b in buttons_text.split(";"):
            name, url = b.split("|")
            buttons.append({"text": name.strip(), "url": url.strip()})
    except:
        return await message.reply("❗ Формат кнопок: Название|URL;Кнопка2|URL2")
    
    settings = {}
    if os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
    
    settings["buttons"] = buttons
    with open(WELCOME_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)
    
    await message.answer("✅ Кнопки приветствия обновлены!")

@dp.message(F.text.startswith("-приветствие"))
async def remove_welcome(message: types.Message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return await message.reply("❌ У вас нет прав для изменения приветствия.")
    if os.path.exists(WELCOME_FILE):
        os.remove(WELCOME_FILE)
    await message.answer("✅ Приветствие отключено!")

@dp.message(F.text.lower() == "приветствие")
async def view_welcome(message: types.Message):
    if os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
        text = settings.get("text", "Не задано")
        media = settings.get("media", "Не задано")
        buttons = settings.get("buttons", [])
        btn_str = "; ".join([f"{b['text']}|{b['url']}" for b in buttons]) if buttons else "Не задано"
        await message.answer(f"📝 Приветствие:\nТекст: {text}\nМедиа: {media}\nКнопки: {btn_str}")
    else:
        await message.answer("❗ Приветствие ещё не настроено.")

@dp.message(F.text.lower() == "тест приветствия")
async def test_welcome(message: types.Message):
    member = message.from_user
    await send_welcome(message.chat.id, member)

# ====== Авто-приветствие новых участников ======
@dp.message(F.new_chat_members)
async def welcome_new_members(message: types.Message):
    for member in message.new_chat_members:
        await send_welcome(message.chat.id, member)

async def send_welcome(chat_id, member):
    settings = {}
    if os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
    
    text = settings.get("text", "Привет, {имя}! Добро пожаловать 😊")
    media = settings.get("media")
    buttons = settings.get("buttons", [])

    text = text.replace("{имя}", member.full_name)\
               .replace("{username}", member.username or "")\
               .replace("{id}", str(member.id))

    keyboard = None
    if buttons:
        keyboard = types.InlineKeyboardMarkup()
        for b in buttons:
            keyboard.add(types.InlineKeyboardButton(text=b["text"], url=b["url"]))

    if media:
        try:
            await bot.send_animation(chat_id, media, caption=text, reply_markup=keyboard)
        except:
            try:
                await bot.send_photo(chat_id, media, caption=text, reply_markup=keyboard)
            except:
                await bot.send_message(chat_id, text, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id, text, reply_markup=keyboard)

# ====== Фильтр слов ======
BAD_WORDS = ["харизма", "xarizma"]

@dp.message()
async def filter_bad_words(message: types.Message):
    if message.text:
        text_lower = message.text.lower()
        if any(word in text_lower for word in BAD_WORDS):
            try:
                await message.delete()
                if ADMIN_ID:
                    await bot.send_message(
                        ADMIN_ID,
                        f"Удалено сообщение пользователя {message.from_user.full_name} "
                        f"({message.from_user.id}):\n{message.text}"
                    )
            except Exception as e:
                print(f"Ошибка удаления: {e}")

# ====== Запуск ======
async def main():
    asyncio.create_task(start_web())
    print("🤖 Бот запущен и работает 24/7")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
