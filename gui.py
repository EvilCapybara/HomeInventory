from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


class Keyboard(InlineKeyboardMarkup):
    def __init__(self):
        super().__init__()

    def skip_keyboard(self):
        self.add(InlineKeyboardButton(text="Пропустить", callback_data="skip"))
        return self
