import json
WELCOME_FILE = "welcome.json"  # теперь хранение настроек в JSON

# ====== Установка приветствия ======
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

# ====== Отправка приветствия новому пользователю ======
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
