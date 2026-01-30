import config
import telebot
from typing import Optional
from gui import Keyboard

# from homemanager import HomeManager

item_data = dict()

# --- словарь переходов между шагами для add ---
ADD_NEXT_STEP = {
    "name": "brand",
    "brand": "model",
    "model": "category",
    "category": "quantity",
    "quantity": "storage_place",
    "storage_place": "belong_to",
    "belong_to": None
}

# --- словарь подсказок для следующих шагов в процессе add ---
ADD_PROMPTS = {
    "name": "Введите название предмета:",
    "brand": "Введите бренд предмета (или 'Пропустить'):",
    "model": "Введите модель (или 'Пропустить'):",
    "category": "Введите категорию (или 'Пропустить'):",
    "quantity": "Введите количество:",
    "storage_place": "Введите место хранения (или 'Пропустить'):",
    "belong_to": "Введите хозяина вещи (или 'Пропустить'):"
}

# --- словарь переходов между шагами для remove ---
EDIT_QUANTITY_NEXT_STEP = {
    "name": "quantity",
    "quantity": None
}

# --- словарь подсказок для следующих шагов в процессе remove ---
REMOVE_PROMPTS = {
    "name": "Пожалуйста, введите название предмета, некоторое количество которых хотите удалить:",
    "quantity": "Введите количество предметов для удаления:"
}

ADD_MORE_PROMPTS = {
    "name": "Пожалуйста, введите название предмета, некоторое количество которых хотите добавить:",
    "quantity": "Введите количество предметов для добавления:"
}

SKIP_STEPS_ADD = ["brand", "model", "category", "storage_place", "belong_to"]


class Bot(telebot.TeleBot):  # TODO добавить status чтобы сразу отправлять есть юзер в базе или нет
    def __init__(self, token):
        super().__init__(token)

        self.user_states = dict()
        self.action_not_started_yet = dict()

    def complete_answering(self, user: telebot.types.User, context: str, data: dict, message: telebot.types.Message):
        ''' если шагов больше нет, сохраняем в БД '''
        # if self.user_states[user.id].get("next_question_exists") is False or None:
        from homemanager import HomeManager

        if context == 'add':
            text = HomeManager().add_new_item(user=user, item_data=data)
        elif context == 'delete':
            text = HomeManager().delete(item_data=data)
        elif context == 'remove':
            text = HomeManager().edit_quantity(item_data=data, context=context)
        elif context == 'add_more':
            text = HomeManager().edit_quantity(item_data=data, context=context)

        # очищаем состояние пользователя
        del self.user_states[user.id]

        # отправляем финальное сообщение
        self.reply_to(message, text)
        return

    def next_step(self, step: str, next_step_list: dict) -> Optional[str]:
        ''' определяем следующий шаг '''
        return next_step_list.get(step)

    def sending_next_question(self, message: telebot.types.Message, prompt: dict, next_step: str, context: str):
        ''' отправляем следующий вопрос '''
        prompt = prompt.get(next_step)
        if context == 'add':
            if next_step in SKIP_STEPS_ADD:
                # добавляем кнопку "Пропустить" для опциональных шагов
                self.reply_to(message=message, text=prompt, reply_markup=Keyboard().skip_keyboard())
            else:
                # обычный текстовый вопрос
                self.reply_to(message=message, text=prompt)
        elif context == 'remove' or 'add_more':
            self.reply_to(message=message, text=prompt)

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
                "step": next(iter(ADD_NEXT_STEP)),  # текущий шаг
                "data": {},  # уже введённые данные
                "action": "add",  # какую опцию бот сейчас выполняет
                "next_question_exists": True  # это последний был вопрос?
            }
            self.reply_to(message, "Пожалуйста, введите название.")

            # from homemanager import HomeManager
            # text = HomeManager().add_new_item(user, item_data=item_data)
            # self.reply_to(message, text)

        @self.message_handler(commands=['delete'])
        def delete(message):
            user = message.from_user
            self.user_states[user.id] = {
                "data": {},
                "action": "delete"
            }
            self.reply_to(message, "Пожалуйста, введите название предметов, который хотите удалить.")

        @self.message_handler(commands=['remove'])
        def remove(message):
            user = message.from_user
            self.user_states[user.id] = {
                "step": next(iter(EDIT_QUANTITY_NEXT_STEP)),
                "data": {},
                "action": "remove",
                "next_question_exists": True
            }
            self.reply_to(message, REMOVE_PROMPTS[self.user_states[user.id]["step"]])

        @self.message_handler(commands=['addmore'])
        def add_more(message):
            user = message.from_user
            self.user_states[user.id] = {
                "step": next(iter(EDIT_QUANTITY_NEXT_STEP)),
                "data": {},
                "action": "add_more",
                "next_question_exists": True
            }
            self.reply_to(message, ADD_MORE_PROMPTS[self.user_states[user.id]["step"]])

        @self.message_handler(func=lambda m: True)
        def steps_handler(message):
            user = message.from_user

            if user.id not in self.user_states:
                return  # пользователь не в режиме добавления

            state: dict = self.user_states[user.id]
            action: str = state["action"]
            step: str = state.get("step")
            data: dict = state["data"]

            # --- ACTION == ADD ---
            if action == 'add':
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

                # --- определяем следующий шаг ---
                next_step = self.next_step(step=step, next_step_list=ADD_NEXT_STEP)
                self.user_states[user.id]['step'] = next_step
                self.user_states[user.id]["next_question_exists"] = True if next_step else False

                if not next_step:
                    # --- если шагов больше нет, сохраняем в БД ---
                    self.complete_answering(user=user, data=data, message=message, context=action)
                else:
                    # --- отправляем следующий вопрос ---
                    self.sending_next_question(message=message, prompt=ADD_PROMPTS, next_step=next_step, context=action)

            # --- ACTION == REMOVE or ADD MORE ---
            if action == 'remove' or action == 'add_more':
                # --- сохраняем текст пользователя в data ---
                if step == "name":
                    data["name"] = message.text
                elif step == 'quantity':
                    data["quantity"] = int(message.text)

                next_step: Optional[str] = self.next_step(step=step, next_step_list=EDIT_QUANTITY_NEXT_STEP)
                self.user_states[user.id]['step'] = next_step
                self.user_states[user.id]["next_question_exists"] = True if next_step else False

                if not next_step:
                    self.complete_answering(user=user, data=data, message=message, context=action)
                elif action == 'remove':
                    self.sending_next_question(message=message, prompt=REMOVE_PROMPTS, next_step=next_step,
                                               context=action)
                else:
                    self.sending_next_question(message=message, prompt=ADD_MORE_PROMPTS, next_step=next_step,
                                               context=action)

            # --- ACTION == DELETE ---
            if action == 'delete':
                data["name"] = message.text
                self.complete_answering(user=user, data=data, message=message, context=action)

    # def handle_input(self, user):
    #     @self.message_handler(func=lambda message: True)
    #     def input_handler(message):
    #
    #         if user.id not in self.user_states:
    #             return
    #
    #         state = self.user_states[user.id]
    #
    #         item_name = message.text
    #         from homemanager import HomeManager
    #
    #         if state["action"] == "delete":
    #             text = HomeManager().handle_delete(name=item_name)
    #         elif state["action"] == "remove":
    #             text = HomeManager().remove(user=user, item_data=item_data)
    #
    #         del self.user_states[user.id]
    #         self.reply_to(message, text)
