import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram import F
from aiogram.types import CallbackQuery
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
AI_TOKEN = os.getenv("AI_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_USERNAME")

dp = Dispatcher()
history = {}

async def generate_response(user_id: int, prompt: str):
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=AI_TOKEN,
        default_headers={
            "HTTP-Referer": "https://t.me/SmartGDZ_Bot",
            "X-Title": "SmartGDZ Bot"
        }
    )

    if user_id not in history:
        history[user_id] = []

    messages = history[user_id]

    if not any(m["role"] == "system" for m in messages):
        messages.insert(0, {
            "role": "system",
            "content": (
                "Ти освічений і доброзичливий асистент, який допомагає школярам робити домашні завдання. "
                "Твої відповіді мають бути короткими, зрозумілими й українською мовою. "
                "Якщо запит поганий — поясни чому."
            )
        })

    messages.append({"role": "user", "content": prompt})

    try:
        completion = await client.chat.completions.create(
            model="meta-llama/llama-4-maverick:free",
            messages=messages
        )
        response = completion.choices[0].message.content

        messages.append({"role": "assistant", "content": response})
        history[user_id] = messages[-10:]

        return response

    except Exception as e:
        print("Помилка:", e)
        return "⚠️ Виникла помилка при генерації відповіді. Спробуй ще раз або напиши розробнику: @requnex_software"


@dp.message(CommandStart())
async def command_start_handler(message: Message, bot: Bot) -> None:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=message.from_user.id)

        if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]:
            raise ValueError("Not subscribed")

    except (TelegramBadRequest, ValueError):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Підписатися на канал", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")],
            [InlineKeyboardButton(text="✅ Я підписався", callback_data="check_subscription")]
        ])
        await message.answer(
            "❗️Щоб користуватись ботом, потрібно підписатися на наш канал новин.",
            reply_markup=keyboard
        )
        return


    await message.answer(
        "👋 Привіт!\n\n"
        "Я — <b>SmartGDZ Бот</b>, і я допоможу тобі з домашкою! ✍️📚\n"
        "Просто напиши мені запитання, і я дам відповідь.\n\n"
        "🧠 Працюю на базі ШІ Llama 4 Maverick\n"
        "💬 Пиши будь-які шкільні задачі або теми\n\n"
        "🛠️ Бот працює у режимі бета-версії\n\n"
        "📞 Якщо є питання або знайшов баг — пиши @requnex_software",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "check_subscription")
async def start_check_handler(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    chat_member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)

    if chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
        await callback.message.delete()
        await command_start_handler(callback.message)
    else:
        await callback.answer("❗ Щоб користуватись ботом, потрібно підписатись на канал!", show_alert=True)

async def is_subscribed(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status not in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]
    except Exception as e:
        print(f"Помилка при перевірці підписки: {e}")
        return False

@dp.message(F.text)
async def echo_handler(message: Message) -> None:
    bot = message.bot
    subscribed = await is_subscribed(bot, message.from_user.id)
    if not subscribed:
        await message.answer(
            f"🚫 Щоб користуватися ботом, підпишіться на канал: {CHANNEL_ID}\n"
            "Після підписки напишіть будь-яке повідомлення знову."
        )
        return

    msg = await message.answer("🔄 Генерую відповідь, зачекай...")
    response = await generate_response(message.from_user.id, message.text)
    await msg.delete()
    await message.answer(response)

async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
