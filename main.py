"""
Entry point for the HomeInventory Telegram bot.

Initializes the Bot instance and registers all command/callback handlers at
import time. The HomeManager singleton and long-polling loop are started in
main() / __main__ guard.
"""

import config
from api import Bot
from homemanager import HomeManager

bot = Bot(token=config.API_TOKEN)  # инициализация бота
bot.register_handlers()


def main():
    """Initialize the HomeManager singleton before starting the polling loop."""
    home_manager = HomeManager()
    # cli.delete()
    # home_manager.welcome_view()


if __name__ == "__main__":
    try:
        main()
        print("Bot is waiting...")
        bot.infinity_polling()
    except Exception as e:
        raise
