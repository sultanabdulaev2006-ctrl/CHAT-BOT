import os
import asyncio
import time
import re
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ====== Настройки ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан!")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# ====== Веб-сервер для Render ======
async def handle(request):
    return web.Response(text="🤖 Сири Премиум работает 🚀")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.getenv("PORT", 8000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Web server running on port {port}")

# ====== База данных в памяти ======
USERS = {}  # user_id: {nick, rank, emoji, premium}
NOTES = {}  # user_id: [{id, content}]
TODOS = {}  # user_id: [{id, task, done}]
USER_WARNS = {}  # user_id: count
SPAM_TRACKER = {}  # user_id: [timestamps]
BAD_WORDS = ["харизма", "xarizma"]
WELCOME_TEXT = "Привет, (имя)!"   # дефолт
FAREWELL_TEXT = "Пока, (имя)!"   # дефолт
WARN_LIMIT = 3

# ====== Клавиатуры ======
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📁 Профиль", callback_data="menu_profile")],
        [InlineKeyboardButton("🗂 Органайзер", callback_data="menu_organizer")],
        [InlineKeyboardButton("🛠 Чат-управление", callback_data="menu_chat")],
        [InlineKeyboardButton("💎 Премиум", callback_data="menu_premium")],
        [InlineKeyboardButton("👋 Приветствие/Прощание", callback_data="menu_greetings")]
    ])

# ====== /start ======
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in USERS:
        USERS[user_id] = {"nick": message.from_user.full_name, "rank": "Пользователь", "emoji": "🙂", "premium": False}
        NOTES[user_id] = []
        TODOS[user_id] = []
    await message.answer(f"Привет, {message.from_user.full_name}! 👋\nЯ Сири Премиум 🤖", reply_markup=main_menu())

# ====== Приветствие / Прощание ======
@dp.callback_query(F.data == "menu_greetings")
async def menu_greetings(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только админ может менять приветствия/прощания")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✏ Изменить приветствие", callback_data="set_welcome")],
        [InlineKeyboardButton("📄 Показать приветствие", callback_data="show_welcome")],
        [InlineKeyboardButton("❌ Удалить приветствие", callback_data="delete_welcome")],
        [InlineKeyboardButton("✏ Изменить прощание", callback_data="set_farewell")],
        [InlineKeyboardButton("📄 Показать прощание", callback_data="show_farewell")],
        [InlineKeyboardButton("❌ Удалить прощание", callback_data="delete_farewell")],
        [InlineKeyboardButton("⬅ Назад", callback_data="back_main")]
    ])
    await call.message.edit_text("👋 Приветствие и прощание", reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data.startswith(("set_", "show_", "delete_")))
async def greetings_actions(call: types.CallbackQuery):
    global WELCOME_TEXT, FAREWELL_TEXT
    action = call.data
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только админ")
        return

    if action == "set_welcome":
        await call.message.answer("Введите новый текст приветствия (используйте (имя) для имени пользователя):")
        @dp.message(F.from_user.id == ADMIN_ID)
        async def set_welcome_text(message: types.Message):
            nonlocal WELCOME_TEXT
            WELCOME_TEXT = message.text
            await message.answer(f"✅ Приветствие обновлено:\n{WELCOME_TEXT}")
            dp.message_handlers.unregister(set_welcome_text)

    elif action == "show_welcome":
        await call.message.answer(f"📄 Текущее приветствие:\n{WELCOME_TEXT}")

    elif action == "delete_welcome":
        WELCOME_TEXT = ""
        await call.message.answer("❌ Приветствие удалено")

    elif action == "set_farewell":
        await call.message.answer("Введите новый текст прощания (используйте (имя) для имени пользователя):")
        @dp.message(F.from_user.id == ADMIN_ID)
        async def set_farewell_text(message: types.Message):
            nonlocal FAREWELL_TEXT
            FAREWELL_TEXT = message.text
            await message.answer(f"✅ Прощание обновлено:\n{FAREWELL_TEXT}")
            dp.message_handlers.unregister(set_farewell_text)

    elif action == "show_farewell":
        await call.message.answer(f"📄 Текущее прощание:\n{FAREWELL_TEXT}")

    elif action == "delete_farewell":
        FAREWELL_TEXT = ""
        await call.message.answer("❌ Прощание удалено")

    await call.answer()

# ====== Авто-приветствие и прощание ======
@dp.message(F.new_chat_members)
async def welcome_new_members(message: types.Message):
    for member in message.new_chat_members:
        text = WELCOME_TEXT.replace("(имя)", member.full_name) if WELCOME_TEXT else f"Привет, {member.full_name}!"
        await message.answer(text)

@dp.message(F.left_chat_member)
async def farewell_member(message: types.Message):
    member = message.left_chat_member
    text = FAREWELL_TEXT.replace("(имя)", member.full_name) if FAREWELL_TEXT else f"Пока, {member.full_name}!"
    await message.answer(text)

# ====== Профиль ======
@dp.callback_query(F.data == "menu_profile")
async def menu_profile(call: types.CallbackQuery):
    user_id = call.from_user.id
    u = USERS.get(user_id)
    if not u:
        await call.answer("❌ Пользователь не найден")
        return
    text = f"👤 Профиль:\nНик: {u['nick']}\nРанг: {u['rank']}\nЭмодзи: {u['emoji']}\nПремиум: {'✅' if u['premium'] else '❌'}"
    await call.message.edit_text(text, reply_markup=main_menu())
    await call.answer()

# ====== Органайзер ======
@dp.callback_query(F.data == "menu_organizer")
async def menu_organizer(call: types.CallbackQuery):
    user_id = call.from_user.id
    notes = NOTES.get(user_id, [])
    todos = TODOS.get(user_id, [])
    text = f"🗂 Ваш органайзер:\n\n📌 Заметки:\n"
    text += "\n".join(f"{i+1}. {n['content']}" for i, n in enumerate(notes)) or "Нет заметок"
    text += "\n\n✅ Задачи:\n"
    text += "\n".join(f"{i+1}. [{'✔' if t['done'] else '❌'}] {t['task']}" for i, t in enumerate(todos)) or "Нет задач"
    await call.message.edit_text(text, reply_markup=main_menu())
    await call.answer()

# ====== Чат-управление (варн, мут, бан, кик) ======
async def log_action(action, target: types.User, by_user: types.User, reason=""):
    if ADMIN_ID:
        await bot.send_message(
            ADMIN_ID,
            f"📝 <b>Модерация:</b> {action}\n"
            f"👤 Пользователь: {target.full_name} ({target.id})\n"
            f"👮 Модератор: {by_user.full_name} ({by_user.id})\n"
            f"📌 Причина: {reason}\n"
            f"⏰ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
            parse_mode=ParseMode.HTML
        )

async def warn_user(message: types.Message, target: types.User, reason: str):
    uid = target.id
    count = USER_WARNS.get(uid, 0) + 1
    USER_WARNS[uid] = count
    await message.answer(f"⚠ Пользователь {target.full_name} получил варн {count}/{WARN_LIMIT}\nПричина: {reason}")
    await log_action("Варн", target, message.from_user, reason)
    if count >= WARN_LIMIT:
        await ban_user(message, target, "Превышен лимит варнов")

async def ban_user(message: types.Message, target: types.User, reason: str):
    try:
        await message.chat.kick(target.id)
        await message.answer(f"🔨 Пользователь {target.full_name} забанен\nПричина: {reason}")
        await log_action("Бан", target, message.from_user, reason)
    except Exception as e:
        await message.answer(f"❌ Не удалось забанить: {e}")

async def kick_user(message: types.Message, target: types.User):
    try:
        await message.chat.kick(target.id)
        await message.answer(f"👢 Пользователь {target.full_name} кикнут!")
        await log_action("Кик", target, message.from_user)
    except Exception as e:
        await message.answer(f"❌ Не удалось кикнуть: {e}")

@dp.message(F.text.startswith("варн"))
async def cmd_warn(message: types.Message):
    parts = message.text.split()
    if len(parts) < 3 or not message.entities:
        return await message.reply("❗ Использование: варн @user причина")
    target = message.entities[1].user
    reason = " ".join(parts[2:])
    await warn_user(message, target, reason)

@dp.message(F.text.startswith("бан"))
async def cmd_ban(message: types.Message):
    parts = message.text.split()
    if len(parts) < 3 or not message.entities:
        return await message.reply("❗ Использование: бан @user причина")
    target = message.entities[1].user
    reason = " ".join(parts[2:])
    await ban_user(message, target, reason)

@dp.message(F.text.startswith("кик"))
async def cmd_kick(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2 or not message.entities:
        return await message.reply("❗ Использование: кик @user")
    target = message.entities[1].user
    await kick_user(message, target)

# ====== Анти-капс, анти-спам, фильтр слов ======
@dp.message()
async def chat_filters(message: types.Message):
    text = message.text
    uid = message.from_user.id
    now = time.time()
    # Анти-капс
    if text and len(text) > 5 and text.isupper():
        try: await message.delete(); await message.answer(f"🔇 Не кричите, {message.from_user.full_name}!")
        except: pass
    # Анти-спам
    stamps = SPAM_TRACKER.get(uid, [])
    stamps = [t for t in stamps if now - t < 5]
    stamps.append(now)
    SPAM_TRACKER[uid] = stamps
    if len(stamps) > 5:
        try: await message.delete(); await message.answer(f"🚫 Спам запрещён, {message.from_user.full_name}!")
        except: pass
    # Фильтр плохих слов
    if any(w in text.lower() for w in BAD_WORDS):
        try: await message.delete()
        except: pass

# ====== Запуск ======
async def main():
    asyncio.create_task(start_web())
    print("🤖 Сири Премиум запущена и работает 24/7")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
