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
WARN_LIMIT = 3
USER_WARNS = {}  # user_id: count
SPAM_TRACKER = {}  # user_id: [timestamps]
BAD_WORDS = ["харизма", "xarizma"]

# ====== Переменные приветствия и прощания ======
WELCOME_TEXT = "Привет, (имя)!"
FAREWELL_TEXT = "Пока, (имя)!"

# ====== Клавиатуры ======
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📁 Профиль", callback_data="menu_profile")],
        [InlineKeyboardButton("🗂 Органайзер", callback_data="menu_organizer")],
        [InlineKeyboardButton("🛠 Чат-управление", callback_data="menu_chat")],
        [InlineKeyboardButton("💎 Премиум", callback_data="menu_premium")]
    ])

def profile_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✏ Изменить ник", callback_data="profile_nick")],
        [InlineKeyboardButton("⭐ Изменить ранк", callback_data="profile_rank")],
        [InlineKeyboardButton("😊 Изменить эмодзи", callback_data="profile_emoji")],
        [InlineKeyboardButton("⬅ Назад", callback_data="back_main")]
    ])

def organizer_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("➕ Добавить заметку", callback_data="organizer_add_note")],
        [InlineKeyboardButton("📄 Список заметок", callback_data="organizer_list_notes")],
        [InlineKeyboardButton("➕ Добавить todo", callback_data="organizer_add_todo")],
        [InlineKeyboardButton("📋 Список todo", callback_data="organizer_list_todo")],
        [InlineKeyboardButton("⬅ Назад", callback_data="back_main")]
    ])

def premium_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("💎 Выдать премиум", callback_data="premium_grant")],
        [InlineKeyboardButton("❌ Снять премиум", callback_data="premium_revoke")],
        [InlineKeyboardButton("⬅ Назад", callback_data="back_main")]
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
@dp.message(F.new_chat_members)
async def welcome_new_members(message: types.Message):
    for member in message.new_chat_members:
        text = WELCOME_TEXT.replace("(имя)", member.full_name)
        await message.answer(text)

@dp.message(F.left_chat_member)
async def farewell_member(message: types.Message):
    member = message.left_chat_member
    text = FAREWELL_TEXT.replace("(имя)", member.full_name)
    await message.answer(text)

# ====== Профиль ======
@dp.callback_query(F.data.startswith("menu_profile"))
async def menu_profile(call: types.CallbackQuery):
    user = USERS.get(call.from_user.id)
    text = (
        f"👤 Ник: {user['nick']}\n"
        f"⭐ Ранг: {user['rank']}\n"
        f"😊 Эмодзи: {user['emoji']}\n"
        f"💎 Статус: {'Premium' if user['premium'] else 'Обычный'}"
    )
    await call.message.edit_text(text, reply_markup=profile_menu())
    await call.answer()

# ====== Изменение профиля ======
@dp.callback_query(F.data.startswith("profile_"))
async def edit_profile(call: types.CallbackQuery):
    field = call.data.split("_")[1]
    await call.message.answer(f"Введите новое значение для {field}:")
    
    @dp.message(F.from_user.id == call.from_user.id)
    async def receive_input(message: types.Message):
        if field == "nick":
            USERS[message.from_user.id]["nick"] = message.text
        elif field == "rank":
            USERS[message.from_user.id]["rank"] = message.text
        elif field == "emoji":
            USERS[message.from_user.id]["emoji"] = message.text
        await message.answer(f"✅ {field} обновлено!", reply_markup=profile_menu())
        dp.message_handlers.unregister(receive_input)

# ====== Органайзер ======
@dp.callback_query(F.data.startswith("menu_organizer"))
async def menu_organizer(call: types.CallbackQuery):
    await call.message.edit_text("🗂 Органайзер", reply_markup=organizer_menu())
    await call.answer()

@dp.callback_query(F.data.startswith("organizer_"))
async def organizer_actions(call: types.CallbackQuery):
    user_id = call.from_user.id
    action = call.data.split("_")[1]
    if action == "add":
        await call.message.answer("Введите текст заметки:")
        @dp.message(F.from_user.id == call.from_user.id)
        async def add_note_input(message: types.Message):
            NOTES[user_id].append({"id": len(NOTES[user_id])+1, "content": message.text})
            await message.answer("✅ Заметка добавлена!", reply_markup=organizer_menu())
            dp.message_handlers.unregister(add_note_input)
    elif action == "list":
        notes = NOTES.get(user_id, [])
        if not notes:
            await call.message.answer("📄 Нет заметок")
        else:
            text = "\n".join([f"{n['id']}. {n['content']}" for n in notes])
            await call.message.answer(f"📄 Заметки:\n{text}", reply_markup=organizer_menu())

# ====== Премиум ======
@dp.callback_query(F.data.startswith("menu_premium"))
async def menu_premium(call: types.CallbackQuery):
    await call.message.edit_text("💎 Панель премиум", reply_markup=premium_menu())
    await call.answer()

@dp.callback_query(F.data.startswith("premium_"))
async def premium_actions(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Только админ может управлять премиумом")
        return
    user_id = int(call.message.text.split("ID: ")[-1]) if "ID:" in call.message.text else call.from_user.id
    if call.data == "premium_grant":
        USERS[user_id]["premium"] = True
        await call.message.answer("✅ Премиум выдан!")
    elif call.data == "premium_revoke":
        USERS[user_id]["premium"] = False
        await call.message.answer("❌ Премиум снят!")

# ====== Чат-управление / Модерация ======
async def log_action(action, target, by_user, reason=""):
    if ADMIN_ID:
        await bot.send_message(
            ADMIN_ID,
            f"📝 <b>{action}</b>\n"
            f"👤 Пользователь: {target.full_name} ({target.id})\n"
            f"👮 Модератор: {by_user.full_name} ({by_user.id})\n"
            f"📌 Причина: {reason}\n"
            f"⏰ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}",
            parse_mode="HTML"
        )

async def warn_user(message, target, reason):
    uid = target.id
    count = USER_WARNS.get(uid, 0) + 1
    USER_WARNS[uid] = count
    await message.answer(f"⚠ Пользователь {target.full_name} получил варн {count}/{WARN_LIMIT}\nПричина: {reason}")
    await log_action("Варн", target, message.from_user, reason)
    if count >= WARN_LIMIT:
        await ban_user(message, target, "Превышен лимит варнов")

async def ban_user(message, target, reason):
    try:
        await message.chat.kick(target.id)
        await message.answer(f"🔨 Пользователь {target.full_name} забанен\nПричина: {reason}")
        await log_action("Бан", target, message.from_user, reason)
    except:
        await message.answer("❌ Не удалось забанить")

@dp.message(F.text.startswith("варн"))
async def cmd_warn(message: types.Message):
    if not message.entities or len(message.entities) < 2: return
    target = message.entities[1].user
    reason = " ".join(message.text.split()[2:]) or "Причина не указана"
    await warn_user(message, target, reason)

@dp.message(F.text.startswith("бан"))
async def cmd_ban(message: types.Message):
    if not message.entities or len(message.entities) < 2: return
    target = message.entities[1].user
    reason = " ".join(message.text.split()[2:]) or "Причина не указана"
    await ban_user(message, target, reason)

# ====== Анти-спам и фильтры ======
@dp.message()
async def anti_spam_filter(message: types.Message):
    uid = message.from_user.id
    now = time.time()
    timestamps = SPAM_TRACKER.get(uid, [])
    timestamps = [t for t in timestamps if now - t < 5]
    timestamps.append(now)
    SPAM_TRACKER[uid] = timestamps
    if len(timestamps) > 5:
        try:
            await message.delete()
            await message.answer(f"🚫 Спам запрещён, {message.from_user.full_name}!")
        except:
            pass
    text_lower = message.text.lower() if message.text else ""
    if any(word in text_lower for word in BAD_WORDS):
        try:
            await message.delete()
        except:
            pass

# ====== Запуск ======
async def main():
    asyncio.create_task(start_web())
    print("🤖 Сири Премиум запущена и работает 24/7")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
