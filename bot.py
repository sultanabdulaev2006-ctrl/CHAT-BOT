import os
import asyncio
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

WELCOME_FILE = "welcome.txt"  # файл для хранения приветствия

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

# ====== Команда установки приветствия ======
@dp.message(F.text.startswith("+приветствие"))
async def set_welcome(message: types.Message):

    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return await message.reply("❌ У вас нет прав для изменения приветствия.")

    text = message.text[len("+приветствие"):].strip()

    if not text:
        return await message.reply("❗ Введите текст приветствия.\n"
                                   "Пример: +приветствие Привет, (имя)! Добро пожаловать 😊")

    with open(WELCOME_FILE, "w", encoding="utf-8") as f:
        f.write(text)

    await message.answer("✅ Приветствие беседы обновлено!")


# ====== Приветствие новых участников ======
@dp.message(F.new_chat_members)
async def welcome_new_members(message: types.Message):

    # читаем текст приветствия
    if os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, "r", encoding="utf-8") as f:
            template = f.read()
    else:
        template = "Привет, (имя)! Добро пожаловать 😊"

    for member in message.new_chat_members:
        # подставляем имя по примеру Iris
        text = template.replace("(имя)", member.full_name)

        # отправляем приветствие
        await message.answer(
            f"🗂️ Приветствие беседы:\n{text}"
        )

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
