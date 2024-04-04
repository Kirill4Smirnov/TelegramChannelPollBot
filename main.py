import os
import time
from dotenv import load_dotenv
from telegram import Poll, PollOption
from telegram.ext import Updater, CommandHandler

#private tokens will be loaded later
BOT_TOKEN = ''
CHANNEL_ID = ''


def load_secret_tokens():
    global BOT_TOKEN
    global CHANNEL_ID
    load_dotenv()

    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    CHANNEL_ID = os.environ.get("CHANNEL_ID")


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="I'm a bot that posts polls to your Telegram channel!")


def post_poll(context):
    # Create the poll
    poll = Poll(
        question="What's your favorite color?",
        options=[
            PollOption(text="Red", voter_count=0),
            PollOption(text="Green", voter_count=0),
            PollOption(text="Blue", voter_count=0)
        ],
        is_anonymous=True,
        type=Poll.REGULAR,
        allows_multiple_answers=False,
        correct_option_id=None,
        explanation=None,
        open_period=None,
        close_date=None
    )

    # Send the poll to the Telegram channel
    context.bot.send_poll(chat_id=CHANNEL_ID, poll=poll)


def main():
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Add the /start command handler
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    # Schedule the post_poll function to run every 24 hours
    job_queue = updater.job_queue
    job_queue.run_repeating(post_poll, interval=86400, first=0)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    pass
