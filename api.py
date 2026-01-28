import config
import telebot
from gui import Keyboard
# from homemanager import HomeManager

item_data = dict()
next_step = True

# --- словарь переходов между шагами ---
NEXT_STEP = {
    "name": "brand",
    "brand": "model",
    "model": "category",
    "category": "quantity",
    "quantity": "storage_place",
    "storage_place": "belong_to",
    "belong_to": None
}

# --- словарь подсказок для следующих шагов ---
PROMPTS = {
    "name": "Введите название предмета:",
    "brand": "Введите бренд предмета (или 'Пропустить'):",
    "model": "Введите модель (или 'Пропустить'):",
    "category": "Введите категорию (или 'Пропустить'):",
    "quantity": "Введите количество:",
    "storage_place": "Введите место хранения (или 'Пропустить'):",
    "belong_to": "Введите хозяина вещи (или 'Пропустить'):"
}


class Bot(telebot.TeleBot):  # TODO добавить status чтобы сразу отправлять есть юзер в базе или нет
    def __init__(self, token):
        super().__init__(token)

        self.user_states = dict()

    def register_handlers(self):
        @self.message_handler(commands=['start'])  # хэндлер команды старт
        def start(message):
            user = message.from_user
            from homemanager import HomeManager
            text = HomeManager().handle_start(user)
            self.reply_to(message, text, parse_mode="Markdown")

        @self.message_handler(commands=['show'])
        def view(message):
            user = message.from_user
            from homemanager import HomeManager
            text = HomeManager().handle_view(user)
            self.reply_to(message, text)

        @self.message_handler(commands=['add'])
        def add(message):
            user = message.from_user

            self.user_states[user.id] = {
                "step": "name",  # текущий шаг
                "data": {}  # уже введённые данные
            }
            self.reply_to(message, "Пожалуйста, введите название.")
            # if self.user_states[user.id]["step"] is not None:
            while next_step is not None:
                self.handle_add_steps(user=user)

            from homemanager import HomeManager
            text = HomeManager().add_new_item(user, item_data=item_data)
            self.reply_to(message, text)

        @self.message_handler(commands=['delete'])
        def delete(message):
            user = message.from_user
            self.user_states[user.id] = {
                "action": "delete"
            }
            self.reply_to(message, "Пожалуйста, введите название предмета, который хотите удалить.")

        @self.message_handler(func=lambda message: True)
        def handle_input_text(message):
            print("DEBUG: message received:", message.text)
            # user = message.from_user
            #
            # if user.id not in self.user_states:
            #     return
            #
            # state = self.user_states[user.id]
            #
            # if state["action"] == "delete":
            #     item_name = message.text
            #     from homemanager import HomeManager
            #     text = HomeManager().handle_delete(name=item_name)
            #
            # del self.user_states[user.id]
            # self.reply_to(message, text)

    def handle_add_steps(self, user):
        @self.message_handler(func=lambda m: True)
        def steps_handler(message):
            if user.id not in self.user_states:
                return  # пользователь не в режиме добавления

            state: dict = self.user_states[user.id]
            step: str = state["step"]
            data: dict = state["data"]

            # --- сохраняем текст пользователя в data ---
            if step == "name":
                data["name"] = message.text
            elif step == "brand":
                data["brand"] = message.text
            elif step == "model":
                data["model"] = message.text
            elif step == "category":
                data["category"] = message.text
            elif step == "quantity":
                if not message.text.isdigit():
                    self.reply_to(message, "Пожалуйста, введите число.")
                    return
                data["quantity"] = int(message.text)
            elif step == "storage_place":
                data["storage_place"] = message.text
            elif step == "belong_to":
                data["belong_to"] = message.text
                # data["owner_id"] = "default"

            # --- определяем следующий шаг ---
            next_step = NEXT_STEP.get(step)
            state["step"] = next_step

            # --- если шагов больше нет, сохраняем в БД ---
            if next_step is None:
                from homemanager import HomeManager
                text = HomeManager().add_new_item(user=user, item_data=data)

                # очищаем состояние пользователя
                del self.user_states[user.id]

                # отправляем финальное сообщение
                self.reply_to(message, text)
                return

        # --- отправляем следующий вопрос ---
            prompt = PROMPTS.get(next_step)
            if next_step in ["brand", "model", "category", "storage_place", "belong_to"]:
                # добавляем кнопку "Пропустить" для опциональных шагов
                self.reply_to(message=message, text=prompt, reply_markup=Keyboard().skip_keyboard())
            else:
                # обычный текстовый вопрос
                self.reply_to(message=message, text=prompt)


