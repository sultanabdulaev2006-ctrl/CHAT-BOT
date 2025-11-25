import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types

# ====== Настройки ======
BOT_TOKEN = os.getenv("BOT_TOKEN")       # Токен бота
ADMIN_ID = os.getenv("ADMIN_ID")         # Telegram ID администратора

if not BOT_TOKEN:
    raise ValueError("❌ Переменная BOT_TOKEN не задана!")

ADMIN_ID = int(ADMIN_ID) if ADMIN_ID and ADMIN_ID.isdigit() else None

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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

# ====== Список слов для фильтра ======
BAD_WORDS = ["харизма", "xarizma"]  # можно добавить новые формы при необходимости

# ====== Фильтр сообщений ======
@dp.message()
async def filter_bad_words(message: types.Message):
    if message.text:
        text_lower = message.text.lower()  # приводим к нижнему регистру
        if any(word in text_lower for word in BAD_WORDS):
            try:
                await message.delete()
                print(f"Удалено сообщение: {message.text}")
                
                # уведомление админу в ЛС
                if ADMIN_ID:
                    await bot.send_message(
                        ADMIN_ID,
                        f"Удалено сообщение пользователя {message.from_user.full_name} "
                        f"({message.from_user.id}):\n{message.text}"
                    )
            except Exception as e:
                print(f"Не удалось удалить сообщение: {e}")

# ====== Запуск ======
async def main():
    asyncio.create_task(start_web())  # запускаем web-сервер параллельно
    print("🤖 Бот запущен и работает 24/7")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
