import os
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import openai
from db import Database  # Import the Database class

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
dp = Dispatcher()

# OpenAI setup
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize the database
db = Database()

# Load translations
with open("lang.json", "r", encoding="utf-8") as f:
    translations = json.load(f)

# Available GPT models
GPT_MODELS = {
    "gpt-3.5-turbo": "GPT-3.5 Turbo",
    "gpt-4": "GPT-4",
}

async def get_translation(user_id, key, **kwargs):
    """Get translation for a specific key based on the user's language preference."""
    user = db.get_user(user_id)
    lang = user[2] if user else "en"  # Default to English
    return translations[lang][key].format(**kwargs)

async def generate_response(user_id, text):
    """Generate a response using OpenAI's API."""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Default model, can be updated based on user selection
        messages=[{"role": "user", "content": text}]
    )
    reply = response['choices'][0]['message']['content']
    db.save_prompt(user_id, text, reply)  # Save the prompt and response
    return reply

@dp.message(Command("start"))
async def send_welcome(message: Message):
    """Handle the /start command."""
    user_id = message.from_user.id
    username = message.from_user.username
    db.add_user(user_id, username)  # Add user to the database
    welcome_text = await get_translation(user_id, "welcome")
    await message.reply(welcome_text)

@dp.message(Command("premium"))
async def premium_info(message: Message):
    """Handle the /premium command."""
    user_id = message.from_user.id
    premium_text = await get_translation(user_id, "premium_info")
    premium_button = await get_translation(user_id, "premium_button")
    
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text=premium_button,
        callback_data="get_premium")
    )
    await message.answer(premium_text, reply_markup=builder.as_markup())

@dp.callback_query(F.data == "get_premium")
async def process_premium(callback: CallbackQuery):
    """Handle premium subscription callback."""
    user_id = callback.from_user.id
    db.add_premium(user_id, days=30, prompt_limit=100)  # Add premium subscription
    success_text = await get_translation(user_id, "premium_success")
    await callback.answer(success_text, show_alert=True)

@dp.message(Command("model"))
async def select_model(message: Message):
    """Handle the /model command to select GPT model."""
    user_id = message.from_user.id
    select_model_text = await get_translation(user_id, "select_model")
    
    builder = InlineKeyboardBuilder()
    for model_key, model_name in GPT_MODELS.items():
        builder.add(types.InlineKeyboardButton(
            text=model_name,
            callback_data=f"select_model_{model_key}")
        )
    builder.adjust(1)  # Arrange buttons in one column
    await message.answer(select_model_text, reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("select_model_"))
async def process_model_selection(callback: CallbackQuery):
    """Handle GPT model selection callback."""
    user_id = callback.from_user.id
    model_key = callback.data.split("_")[2]  # Extract the model key
    model_name = GPT_MODELS[model_key]
    success_text = await get_translation(user_id, "model_selected", model_name=model_name)
    await callback.answer(success_text, show_alert=True)

@dp.message(Command("language"))
async def select_language(message: Message):
    """Handle the /language command to select language."""
    user_id = message.from_user.id
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="English", callback_data="set_lang_en"))
    builder.add(types.InlineKeyboardButton(text="Русский", callback_data="set_lang_ru"))
    builder.adjust(1)
    await message.answer("Select your language:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("set_lang_"))
async def process_language_selection(callback: CallbackQuery):
    """Handle language selection callback."""
    user_id = callback.from_user.id
    lang = callback.data.split("_")[2]  # Extract the language code
    db.update_user_language(user_id, lang)  # Update user's language preference
    await callback.answer(f"Language set to {lang}", show_alert=True)

@dp.message(F.text)
async def echo(message: Message):
    """Handle text messages."""
    user_id = message.from_user.id
    if not db.is_premium_active(user_id):  # Check if user has an active premium subscription
        premium_required_text = await get_translation(user_id, "premium_required")
        await message.reply(premium_required_text)
        return
    
    response_text = await generate_response(user_id, message.text)
    db.increment_prompt_count(user_id)  # Increment prompt count for premium users
    await message.reply(response_text)

@dp.message(F.document)
async def handle_document(message: Message):
    """Handle document uploads."""
    user_id = message.from_user.id
    if not db.is_premium_active(user_id):  # Check if user has an active premium subscription
        premium_required_text = await get_translation(user_id, "premium_required")
        await message.reply(premium_required_text)
        return
    
    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    downloaded_file = await bot.download_file(file_path)
    
    with open(f"user_files/{file_id}.txt", "wb") as new_file:
        new_file.write(downloaded_file.read())
    
    file_saved_text = await get_translation(user_id, "file_saved")
    await message.reply(file_saved_text)

async def main() -> None:
    """Start the bot."""
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())