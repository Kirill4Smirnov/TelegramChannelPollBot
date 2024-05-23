import os
from datetime import datetime, timedelta, timezone
import logging
from telegram import (
    KeyboardButton,
    KeyboardButtonPollType,
    Poll,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)
from dotenv import load_dotenv

INTERVAL = timedelta(days=1)
START_TIME = datetime.now(tz=timezone(timedelta(hours=3)))
START_TIME = (START_TIME + timedelta(days=1)).replace(hour=8, minute=0)

# private tokens will be loaded later
BOT_TOKEN = ''
CHANNEL_ID = ''


def load_secret_tokens():
    global BOT_TOKEN
    global CHANNEL_ID
    load_dotenv()

    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    CHANNEL_ID = os.environ.get("CHANNEL_ID")


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

TOTAL_VOTER_COUNT = 3


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inform user about what this bot can do"""
    await update.message.reply_text(
        "Please select /poll to get a Poll, /poll_to_channel to send The Poll to The Channel."
        "You can also /enable_polling or /disable_polling to The Channel"
    )


async def send_message_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a test message to a chat with predefined id"""
    await update._bot.send_message(CHANNEL_ID, "test message")


async def send_poll_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send poll about night dreams to a channel with predefined id"""
    date = datetime.today().strftime('%d.%m')
    questions = ["Не помню", "Без снов", "Нейтральный сон", "Приятное сновидение", "Неприятное сновидение / кошмар",
                 "Несуразный бред", "Смешанные эмоции"]
    await update._bot.send_poll(
        CHANNEL_ID,
        f"Сегодняшние сновидения {date}",
        questions,
        is_anonymous=True,
        allows_multiple_answers=False,
    )


async def send_poll_to_channel_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send poll about night dreams to a channel with predefined id"""
    date = datetime.today().strftime('%d.%m')
    questions = ["Не помню", "Без снов", "Нейтральный сон", "Приятное сновидение", "Неприятное сновидение / кошмар",
                 "Несуразный бред", "Смешанные эмоции"]
    await context.bot.send_poll(
        CHANNEL_ID,
        f"Сегодняшние сновидения {date}",
        questions,
        is_anonymous=True,
        allows_multiple_answers=False,
    )


async def poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a predefined poll"""
    questions = ["Good", "Really good", "Fantastic", "Great"]
    message = await context.bot.send_poll(
        update.effective_chat.id,
        "How are you?",
        questions,
        is_anonymous=False,
        allows_multiple_answers=True,
    )
    # Save some info about the poll the bot_data for later use in receive_poll_answer
    payload = {
        message.poll.id: {
            "questions": questions,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "answers": 0,
        }
    }
    context.bot_data.update(payload)


async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Summarize a users poll vote"""
    answer = update.poll_answer
    answered_poll = context.bot_data[answer.poll_id]
    try:
        questions = answered_poll["questions"]
    # this means this poll answer update is from an old poll, we can't do our answering then
    except KeyError:
        return
    selected_options_ids = answer.option_ids
    answer_string = ""
    for question_id in selected_options_ids:
        if question_id != selected_options_ids[-1]:
            answer_string += questions[question_id] + " and "
        else:
            answer_string += questions[question_id]
    await context.bot.send_message(
        answered_poll["chat_id"],
        f"{update.effective_user.mention_html()} feels {answer_string}!",
        parse_mode=ParseMode.HTML,
    )
    answered_poll["answers"] += 1
    # Close poll after three participants voted
    if answered_poll["answers"] == TOTAL_VOTER_COUNT:
        await context.bot.stop_poll(answered_poll["chat_id"], answered_poll["message_id"])


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a help message"""
    await update.message.reply_text("Use /poll, /poll_to_channel to test this bot. You can also "
                                    "/enable_polling or /disable_polling to The Channel")

def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def enable_regular_polling(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_message.chat_id

    job_removed = remove_job_if_exists(str(chat_id), context)
    context.job_queue.run_repeating(send_poll_to_channel_job, interval=INTERVAL, first=START_TIME, name=str(chat_id))

    text = "Polling successfully scheduled!"
    if job_removed:
        text += " Old polling was removed."
    await update.effective_message.reply_text(text)


async def disable_regular_polling(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = "Polling job successfully cancelled!" if job_removed else "You have no active pollings."
    await update.message.reply_text(text)

def main() -> None:
    """Run bot."""
    load_secret_tokens()

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("poll", poll))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("poll_to_channel", send_poll_to_channel))
    application.add_handler(CommandHandler("enable_polling", enable_regular_polling))
    application.add_handler(CommandHandler("disable_polling", disable_regular_polling))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
