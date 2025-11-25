import os
import asyncio
import json
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from datetime import datetime, timedelta

# ====== Настройки ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise ValueError("❌ Переменная BOT_TOKEN не задана!")

ADMIN_ID = int(ADMIN_ID) if ADMIN_ID and ADMIN_ID.isdigit() else None

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

WELCOME_FILE = "welcome.json"  # для приветствия
WARNS_FILE = "warns.json"      # для варнов
RULES_FILE = "rules.json"      # для правил

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

# ====== Приветствие ======
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
    text = text.replace("{имя}", member.full_name).replace("{username}", member.username or "").replace("{id}", str(member.id))
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

# ====== Модерация: Варн, Мут, Бан ======
def load_warns():
    if os.path.exists(WARNS_FILE):
        with open(WARNS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_warns(data):
    with open(WARNS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

async def restrict_user(chat_id, user_id, duration_seconds):
    until_date = datetime.utcnow() + timedelta(seconds=duration_seconds)
    await bot.restrict_chat_member(chat_id, user_id, types.ChatPermissions(can_send_messages=False), until_date=until_date)

@dp.message(F.text.startswith("варн"))
async def add_warn(message: types.Message):
    if not message.from_user.id == ADMIN_ID:
        return await message.reply("❌ У вас нет прав выдавать варны.")
    args = message.text.split()
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        reason = " ".join(args[1:]) if len(args) > 1 else "Не указана"
    else:
        return await message.reply("❗ Использование: варн через реплай на пользователя")
    data = load_warns()
    chat_warns = data.get(str(message.chat.id), {})
    chat_warns[str(user.id)] = chat_warns.get(str(user.id), 0) + 1
    data[str(message.chat.id)] = chat_warns
    save_warns(data)
    count = chat_warns[str(user.id)]
    await message.answer(f"⚠️ Выдан варн пользователю {user.full_name} (@{user.username or 'не указано'}).\nВсего предупреждений: {count}/3\nПричина: {reason}")
    if count == 2:
        await restrict_user(message.chat.id, user.id, 1800)  # 30 минут
        await message.answer(f"🔇 Автоматический мут на 30 минут.")
    elif count >= 3:
        await bot.ban_chat_member(message.chat.id, user.id)
        await message.answer(f"🚫 Автоматический бан.")

@dp.message(F.text.startswith("варны"))
async def view_warns(message: types.Message):
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        data = load_warns()
        chat_warns = data.get(str(message.chat.id), {})
        count = chat_warns.get(str(user.id), 0)
        await message.answer(f"⚠️ Варны пользователя {user.full_name}: {count}/3")
    else:
        await message.reply("❗ Использование: варны через реплай на пользователя")

@dp.message(F.text.startswith("снятьварн"))
async def remove_warn(message: types.Message):
    if not message.from_user.id == ADMIN_ID:
        return await message.reply("❌ У вас нет прав снимать варны.")
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        data = load_warns()
        chat_warns = data.get(str(message.chat.id), {})
        chat_warns[str(user.id)] = max(0, chat_warns.get(str(user.id), 0)-1)
        data[str(message.chat.id)] = chat_warns
        save_warns(data)
        await message.answer(f"✅ Варн снят пользователю {user.full_name}")
    else:
        await message.reply("❗ Использование: снятьварн через реплай на пользователя")

@dp.message(F.text.startswith("очиститьварны"))
async def clear_warns(message: types.Message):
    if not message.from_user.id == ADMIN_ID:
        return await message.reply("❌ У вас нет прав очищать варны.")
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        data = load_warns()
        chat_warns = data.get(str(message.chat.id), {})
        chat_warns[str(user.id)] = 0
        data[str(message.chat.id)] = chat_warns
        save_warns(data)
        await message.answer(f"✅ Варны очищены пользователю {user.full_name}")
    else:
        await message.reply("❗ Использование: очиститьварны через реплай на пользователя")

@dp.message(F.text.startswith("мут"))
async def mute_user(message: types.Message):
    if not message.from_user.id == ADMIN_ID:
        return await message.reply("❌ У вас нет прав мутить.")
    args = message.text.split()
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        time_arg = args[1] if len(args) > 1 else "30м"
        reason = " ".join(args[2:]) if len(args) > 2 else "Не указана"
    else:
        await message.reply("❗ Использование: мут через реплай [время] [причина]")
        return
    t = time_arg
    seconds = 0
    if t.endswith("м"):
        seconds = int(t[:-1])*60
    elif t.endswith("ч"):
        seconds = int(t[:-1])*3600
    elif t.endswith("д"):
        seconds = int(t[:-1])*86400
    else:
        seconds = int(t)
    await restrict_user(message.chat.id, user.id, seconds)
    await message.answer(f"🔇 Пользователь {user.full_name} (@{user.username or 'не указано'}) получил мут на {time_arg}.\nПричина: {reason}\nВыдал: @{message.from_user.username}")

@dp.message(F.text.startswith("бан"))
async def ban_user(message: types.Message):
    if not message.from_user.id == ADMIN_ID:
        return await message.reply("❌ У вас нет прав банить.")
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        reason = " ".join(message.text.split()[1:]) if len(message.text.split())>1 else "Не указана"
    else:
        await message.reply("❗ Использование: бан через реплай [причина]")
        return
    await bot.ban_chat_member(message.chat.id, user.id)
    await message.answer(f"🚫 Пользователь {user.full_name} (@{user.username or 'не указано'}) был заблокирован.\nПричина: {reason}")

@dp.message(F.text.startswith("разбан"))
async def unban_user(message: types.Message):
    if not message.from_user.id == ADMIN_ID:
        return await message.reply("❌ У вас нет прав разбанивать.")
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        await bot.unban_chat_member(message.chat.id, user.id)
        await message.answer(f"✅ Пользователь {user.full_name} (@{user.username or 'не указано'}) был разбанен")
    else:
        await message.reply("❗ Использование: разбан через реплай на пользователя")

# ====== Правила чата ======
@dp.message(F.text.startswith("+правила "))
async def set_rules_text(message: types.Message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return await message.reply("❌ У вас нет прав изменять правила.")
    text = message.text[len("+правила "):].strip()
    if not text:
        return await message.reply("❗ Введите текст правил чата.")
    settings = {}
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
    settings["text"] = text
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)
    await message.answer("✅ Текст правил обновлён!")

@dp.message(F.text.startswith("+правила кнопки"))
async def set_rules_buttons(message: types.Message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return await message.reply("❌ У вас нет прав изменять правила.")
    buttons_text = message.text[len("+правила кнопки"):].strip()
    buttons = []
    try:
        for b in buttons_text.split(";"):
            name, url = b.split("|")
            buttons.append({"text": name.strip(), "url": url.strip()})
    except:
        return await message.reply("❗ Формат кнопок: Название|URL;Кнопка2|URL2")
    settings = {}
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
    settings["buttons"] = buttons
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)
    await message.answer("✅ Кнопки правил обновлены!")

@dp.message(F.text.lower() == "правила")
async def view_rules(message: types.Message):
    settings = {}
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
    text = settings.get("text", "Правила ещё не заданы.")
    buttons = settings.get("buttons", [])
    keyboard = None
    if buttons:
        keyboard = types.InlineKeyboardMarkup()
        for b in buttons:
            keyboard.add(types.InlineKeyboardButton(text=b["text"], url=b["url"]))
    await message.answer(text, reply_markup=keyboard)

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
