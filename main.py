import asyncio
import logging
import os
import tempfile

import pytz
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TELEGRAM_TOKEN, TIMEZONE
from database import init_db, add_transaction, undo_last_transaction, get_all_user_ids
from classifier import classify_transaction
from voice import transcribe_voice
from reports import format_daily_report, format_week_report, format_monthly_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
ALMATY_TZ = pytz.timezone(TIMEZONE)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Баланс"), KeyboardButton(text="📅 Неделя")],
        [KeyboardButton(text="🗓 Месяц"), KeyboardButton(text="↩️ Отмена")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Напиши о трате или доходе..."
)

START_TEXT = (
    "👋 Привет! Я твой личный финансист.\n\n"
    "Просто напиши или запиши голосовое о своих тратах или доходах:\n"
    "• *«Потратил 1500 на обед»*\n"
    "• *«Получил зарплату 250000»*\n"
    "• *«Кофе 350 тенге»*\n\n"
    "📊 Каждый день в 22:00 буду присылать сводку\n"
    "📅 30-го числа — полный отчёт за месяц\n\n"
    "Команды:\n"
    "/баланс — сводка за сегодня\n"
    "/неделя — траты за 7 дней\n"
    "/месяц — отчёт за месяц\n"
    "/отмена — отменить последнюю запись"
)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(START_TEXT, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


@dp.message(Command("баланс"))
async def cmd_balance(message: Message):
    report = format_daily_report(message.from_user.id)
    await message.answer(report, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


@dp.message(Command("неделя"))
async def cmd_week(message: Message):
    report = format_week_report(message.from_user.id)
    await message.answer(report, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


@dp.message(Command("месяц"))
async def cmd_month(message: Message):
    report = format_monthly_report(message.from_user.id)
    await message.answer(report, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


@dp.message(Command("отмена"))
async def cmd_undo(message: Message):
    success = undo_last_transaction(message.from_user.id)
    if success:
        await message.answer("↩️ Последняя запись отменена.", reply_markup=MAIN_KEYBOARD)
    else:
        await message.answer("Записей не найдено.", reply_markup=MAIN_KEYBOARD)


@dp.message(F.voice)
async def handle_voice(message: Message):
    await message.answer("🎤 Обрабатываю голосовое...")

    voice = message.voice
    file = await bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        await bot.download_file(file.file_path, tmp.name)
        tmp_path = tmp.name

    try:
        text = transcribe_voice(tmp_path)
        await message.answer(f"🗣 Распознал: _{text}_", parse_mode="Markdown")
        result = classify_transaction(text)
        await process_classification(message, result)
    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        await message.answer("❌ Не смог обработать голосовое. Попробуй написать текстом.")
    finally:
        os.unlink(tmp_path)


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message):
    text = message.text.strip()

    # Обработка кнопок клавиатуры
    if "Баланс" in text:
        await cmd_balance(message)
        return
    if "Неделя" in text:
        await cmd_week(message)
        return
    if "Месяц" in text:
        await cmd_month(message)
        return
    if "Отмена" in text:
        await cmd_undo(message)
        return

    try:
        result = classify_transaction(text)
        await process_classification(message, result)
    except Exception as e:
        logger.error(f"Classification error: {e}", exc_info=True)
        await message.answer(f"❌ Произошла ошибка: `{e}`", parse_mode="Markdown")


async def process_classification(message: Message, result: dict):
    if "error" in result:
        await message.answer(
            "🤔 Не смог понять сумму или тип операции.\n"
            "Попробуй написать яснее, например:\n"
            "• *«Потратил 1500 на такси»*\n"
            "• *«Получил 50000 зарплата»*",
            parse_mode="Markdown"
        )
        return

    add_transaction(
        user_id=message.from_user.id,
        type_=result["type"],
        amount=result["amount"],
        category=result["category"],
        description=result["description"]
    )

    emoji = "💸" if result["type"] == "expense" else "💰"
    type_text = "Расход" if result["type"] == "expense" else "Доход"

    await message.answer(
        f"{emoji} *Записал!*\n"
        f"{type_text}: {result['amount']:,.0f} ₸\n"
        f"Категория: {result['category']}\n"
        f"_{result['description']}_\n\n"
        f"Чтобы отменить — /отмена",
        parse_mode="Markdown"
    )


async def send_daily_reports():
    for user_id in get_all_user_ids():
        try:
            report = format_daily_report(user_id)
            await bot.send_message(user_id, report, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Daily report error for {user_id}: {e}")


async def send_monthly_reports():
    for user_id in get_all_user_ids():
        try:
            report = format_monthly_report(user_id)
            await bot.send_message(user_id, report, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Monthly report error for {user_id}: {e}")


async def main():
    init_db()

    scheduler = AsyncIOScheduler(timezone=ALMATY_TZ)
    scheduler.add_job(send_daily_reports, "cron", hour=22, minute=0)
    scheduler.add_job(send_monthly_reports, "cron", day=30, hour=22, minute=0)
    scheduler.start()

    logger.info("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
