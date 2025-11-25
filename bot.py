import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
import re
import time

# ====== Настройки ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise ValueError("❌ Переменная BOT_TOKEN не задана!")

ADMIN_ID = int(ADMIN_ID) if ADMIN_ID and ADMIN_ID.isdigit() else None

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

WELCOME_FILE = "welcome.txt"
RULES_FILE = "rules.txt"

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
# +приветствие ТЕКСТ — установить новое
@dp.message(F.text.startswith("+приветствие"))
async def set_welcome(message: types.Message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return await message.reply("❌ У вас нет прав")
    text = message.text[len("+приветствие"):].strip()
    if text:
        with open(WELCOME_FILE, "w", encoding="utf-8") as f:
            f.write(text)
        await message.answer("✅ Приветствие обновлено!")

# приветствие — показать текущее
@dp.message(F.text == "приветствие")
async def show_welcome(message: types.Message):
    if os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = "Привет, (имя)!"
    await message.answer(text)

# -приветствие — удалить
@dp.message(F.text == "-приветствие")
async def delete_welcome(message: types.Message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return await message.reply("❌ У вас нет прав")
    if os.path.exists(WELCOME_FILE):
        os.remove(WELCOME_FILE)
    await message.answer("Приветствие удалено!")

# Авто-приветствие новых участников
@dp.message(F.new_chat_members)
async def welcome_new_members(message: types.Message):
    if os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, "r", encoding="utf-8") as f:
            template = f.read()
    else:
        template = "Привет, (имя)!"
    for member in message.new_chat_members:
        text = template.replace("(имя)", member.full_name)
        await message.answer(text)

# ====== Правила ======
@dp.message(F.text.startswith("+правила"))
async def set_rules(message: types.Message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return await message.reply("❌ У вас нет прав для изменения правил.")
    text = message.text[len("+правила"):].strip()
    if not text:
        return await message.reply("❗ Введите текст правил.")
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    await message.answer("✅ Правила обновлены! 📜")

@dp.message(F.text == "правила")
async def show_rules(message: types.Message):
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            rules = f.read()
    else:
        rules = "Правила пока не заданы. 📝"
    await message.answer(f"📌 Правила чата:\n{rules}")

# ====== Мут, Варн, Бан, Кик ======
WARN_LIMIT = 3
user_warns = {}  # {user_id: count}

# ====== Логирование наказаний ======
async def log_action(action_type, target: types.User, by_user: types.User, reason: str):
    if ADMIN_ID:
        await bot.send_message(
            ADMIN_ID,
            f"📝 <b>Модерация:</b> {action_type}\n"
            f"👤 Пользователь: {target.full_name} ({target.id})\n"
            f"👮 Модератор: {by_user.full_name} ({by_user.id})\n"
            f"📌 Причина: {reason}\n"
            f"⏰ Время: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
            parse_mode="HTML"
        )

async def warn_user(message: types.Message, target: types.User, reason: str):
    uid = target.id
    count = user_warns.get(uid, 0) + 1
    user_warns[uid] = count
    await message.answer(f"⚠ Пользователь {target.full_name} получил варн {count}/{WARN_LIMIT} 😎\nПричина: {reason}")
    await log_action("Варн", target, message.from_user, reason)
    if count >= WARN_LIMIT:
        await ban_user(message, target, "Превышен лимит варнов")

async def mute_user(message: types.Message, target: types.User, duration: str):
    await message.answer(f"🤐 Пользователь {target.full_name} замучен на {duration} ⏰")
    await log_action("Мут", target, message.from_user, f"Длительность: {duration}")

async def ban_user(message: types.Message, target: types.User, reason: str):
    try:
        await message.chat.kick(target.id)
        await message.answer(f"🔨 Пользователь {target.full_name} забанен 😎\nПричина: {reason}")
        await log_action("Бан", target, message.from_user, reason)
    except Exception as e:
        await message.answer(f"❌ Не удалось забанить: {e}")

async def kick_user(message: types.Message, target: types.User):
    try:
        await message.chat.kick(target.id)
        await message.answer(f"👢 Пользователь {target.full_name} кикнут!")
        await log_action("Кик", target, message.from_user, "Кик из чата")
    except Exception as e:
        await message.answer(f"❌ Не удалось кикнуть: {e}")

# ====== Команды модерации ======
@dp.message(F.text.startswith("варн"))
async def cmd_warn(message: types.Message):
    parts = message.text.split()
    if len(parts) < 3:
        return await message.reply("❗ Использование: варн @user причина")
    target = message.entities[1].user if len(message.entities) > 1 else None
    reason = " ".join(parts[2:])
    if target:
        await warn_user(message, target, reason)

@dp.message(F.text.startswith("мут"))
async def cmd_mute(message: types.Message):
    parts = message.text.split()
    if len(parts) < 3:
        return await message.reply("❗ Использование: мут 1ч @user причина")
    duration = parts[1]
    target = message.entities[2].user if len(message.entities) > 2 else None
    reason = " ".join(parts[3:])
    if target:
        await mute_user(message, target, duration)

@dp.message(F.text.startswith("бан"))
async def cmd_ban(message: types.Message):
    parts = message.text.split()
    if len(parts) < 3:
        return await message.reply("❗ Использование: бан @user причина")
    target = message.entities[1].user if len(message.entities) > 1 else None
    reason = " ".join(parts[2:])
    if target:
        await ban_user(message, target, reason)

@dp.message(F.text.startswith("кик"))
async def cmd_kick(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        return await message.reply("❗ Использование: кик @user")
    target = message.entities[1].user if len(message.entities) > 1 else None
    if target:
        await kick_user(message, target)

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
                        f"Удалено сообщение пользователя {message.from_user.full_name} ({message.from_user.id}):\n{message.text}"
                    )
            except Exception as e:
                print(f"Ошибка удаления: {e}")

# ====== Очистка сообщений ======
@dp.message(F.text.startswith("очистить"))
async def clear_messages(message: types.Message):
    parts = message.text.split()
    limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
    counter = 0
    async for msg in bot.iter_history(message.chat.id, limit=limit):
        try:
            await bot.delete_message(message.chat.id, msg.message_id)
            counter += 1
        except:
            continue
    await message.answer(f"🧹 Удалено сообщений: {counter} 🧹")

# ====== Команда "кто" ======
@dp.message(F.text.startswith("кто"))
async def who_user(message: types.Message):
    if not message.reply_to_message and not message.entities:
        return await message.reply("❗ Использование: кто @user или в реплее")
    if message.entities:
        target = message.entities[1].user
    else:
        target = message.reply_to_message.from_user
    await message.answer(f"👤 Пользователь: {target.full_name}\nID: {target.id} 📝")

# ====== Анти-капс ======
@dp.message()
async def anti_caps(message: types.Message):
    if message.text and len(message.text) > 5 and message.text.isupper():
        try:
            await message.delete()
            await message.answer(f"🔇 Пожалуйста, не кричите, {message.from_user.full_name}! 😅")
        except:
            pass

# ====== Анти-спам ======
spam_tracker = {}  # {user_id: [timestamps]}

@dp.message()
async def anti_spam(message: types.Message):
    uid = message.from_user.id
    now = time.time()
    timestamps = spam_tracker.get(uid, [])
    timestamps = [t for t in timestamps if now - t < 5]  # 5 сек окно
    timestamps.append(now)
    spam_tracker[uid] = timestamps
    if len(timestamps) > 5:
        try:
            await message.delete()
            await message.answer(f"🚫 Спам запрещён, {message.from_user.full_name}! 😎")
        except:
            pass

# ====== Анти-реклама ======
@dp.message()
async def anti_ads(message: types.Message):
    if message.text and re.search(r"(t\.me\/|telegram\.me|http[s]?:\/\/)", message.text):
        try:
            await message.delete()
            await message.answer(f"📛 Реклама запрещена, {message.from_user.full_name}! ⚠️")
        except:
            pass

# ====== Прощание ======
@dp.message(F.left_chat_member)
async def farewell(message: types.Message):
    member = message.left_chat_member
    await message.answer(f"😢 Пользователь {member.full_name} покинул чат. До новых встреч! 👋")

# ====== Запуск ======
async def main():
    asyncio.create_task(start_web())
    print("🤖 Бот запущен и работает 24/7")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
