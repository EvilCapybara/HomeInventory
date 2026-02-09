from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


# TYPE_BUTTONS = {
#     "Строка": "type:str",
#     "Целое число": "type:int",
#     "Дробное число": "type:float",
#     "Дата": "type:datetime.date",
#     "Да / Нет": "type:bool",
#     "-": "type:none",
# }

TYPE_BUTTONS = {
    "Текст": "type:text",
    "Число (int)": "type:int",
    "Дробное (float)": "type:float",
    "Да/Нет": "type:bool",
    "Дата": "type:date",
}

REQUIRED_BUTTONS = {
    "Обязательное": "required:true",
    "Можно пустое": "required:false",
}

UNIQUE_BUTTONS = {
    "Уникальное": "unique:true",
    "Можно повторять": "unique:false",
}

DEFAULT_CHOICE_BUTTONS = {
    "Задать default": "default_choice:set",
    "Без default": "default_choice:skip",
}

STEP_KEYBOARDS = {
    "type": TYPE_BUTTONS,
    "required": REQUIRED_BUTTONS,
    "unique": UNIQUE_BUTTONS,
    "default_choice": DEFAULT_CHOICE_BUTTONS
}


class Keyboard(InlineKeyboardMarkup):
    def __init__(self):
        super().__init__()
        self.row_width = 2

    def skip_keyboard(self):
        self.add(InlineKeyboardButton(text="Пропустить", callback_data="skip"))

        return self

    def multi_inline(self, buttons: dict):
        # markup = InlineKeyboardMarkup()
        if not buttons:
            return None

        for text, callback in buttons.items():
            self.add(InlineKeyboardButton(text=text, callback_data=callback))

        return self

    def skip_button(self):
        self.add(InlineKeyboardButton(text="Пропустить", callback_data="skip"))

        return self

    def columns_buttons(self, columns: list[str]):
        if not columns:
            return None

        for col in columns:
            self.add(
                InlineKeyboardButton(
                    text=col,
                    callback_data=f"deletecol:{col}"
                )
            )

        # кнопка отмены — очень полезно
        self.add(
            InlineKeyboardButton(
                text="Отмена",
                callback_data="cancel"
            )
        )

        return self

    def rename_columns_buttons(self, columns: list[str]):
        if not columns:
            return None

        for col in columns:
            self.add(
                InlineKeyboardButton(
                    text=col,
                    callback_data=f"renamecol:{col}"
                )
            )

        self.add(InlineKeyboardButton(text="Отмена", callback_data="cancel"))
        return self
