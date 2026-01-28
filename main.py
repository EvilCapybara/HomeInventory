''' Точка входа в программу '''

import logging

import cli
import config
from api import Bot
from homemanager import HomeManager

bot = Bot(token=config.API_TOKEN)  # инициализация бота
bot.register_handlers()


def main():
    ''' Main function. '''
    home_manager = HomeManager()
    # cli.delete()
    # home_manager.welcome_view()
    test_user = TestUser()


class TestUser:
    telegram_id = '1234'
    username = 'capy'
    first_name = 'dasha'


if __name__ == '__main__':
    try:
        main()
        print("Bot is waiting...")
        bot.infinity_polling()
    except Exception as e:
        raise
