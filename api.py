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

# --- словарь переходов между шагами для remove ---
EDIT_QUANTITY_NEXT_STEP = {
    "name": "quantity",
    "quantity": None
}

NEWCOL_NEXT_STEP = {
    "name": "type",
    "type": "constraints",
    "constraints": None
}

RENAME_COL_NEXT_STEP = {
    "old_name": "new_name",
    "new_name": None,
}

SEARCHING_NEXT_STEP = {
    "colname": "value",
    "value": None,
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

# --- словарь подсказок для следующих шагов в процессе remove ---
REMOVE_PROMPTS = {
    "name": "Пожалуйста, введите название предмета, некоторое количество которых хотите удалить:",
    "quantity": "Введите количество предметов для удаления:"
}

ADD_MORE_PROMPTS = {
    "name": "Пожалуйста, введите название предмета, некоторое количество которых хотите добавить:",
    "quantity": "Введите количество предметов для добавления:"
}

NEWCOL_PROMPTS = {
    "name": "Пожалуйста, введите название название для новой колонки:",
    "type": "Введите тип значений в будущей колонке:",
    "constraints": "Введите ограничения для будущей колонки"
}

RENAME_COL_PROMPTS = {
    "old_name": "Пожалуйста, введите текущее название название колонки, которую хотите переименовать:",
    "new_name": "Введите новое имя для колонки:",
}

SEARCHING_PROMPTS = {
    "colname": "Пожалуйста, введите название колонки, объект которой вы хотите найти:",
    "value": "Пожалуйста, введите запрос для поиска объекта по базе данных",
}

SKIP_STEPS = ["brand", "model", "category", "storage_place", "belong_to", "constraints"]


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
        elif context == 'add_newcol':
            text = HomeManager().add_newcol(item_data=data)
        elif context == 'delete_col':
            text = HomeManager().delete_col(item_data=data)
        elif context == 'rename_col':
            text = HomeManager().rename_col(item_data=data)
        elif context == 'find':
            text = HomeManager().find(item_data=data)

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
        if context == 'add' or context == "add_newcol":
            if next_step in SKIP_STEPS:
                # добавляем кнопку "Пропустить" для опциональных шагов
                self.reply_to(message=message, text=prompt, reply_markup=Keyboard().skip_keyboard())
            else:
                # обычный текстовый вопрос
                self.reply_to(message=message, text=prompt)
        else:
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

        @self.message_handler(commands=['delete'])  # TODO ко всем делитам добавить проверочный вопрос "уверены?"
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

        @self.message_handler(commands=['addnewcol'])
        def add_new_col(message):
            user = message.from_user
            self.user_states[user.id] = {
                "step": next(iter(NEWCOL_NEXT_STEP)),
                "data": {},
                "action": "add_newcol",
                "next_question_exists": True
            }
            self.reply_to(message, NEWCOL_PROMPTS[self.user_states[user.id]["step"]])

        @self.message_handler(commands=['deletecol'])
        def delete_col(message):
            user = message.from_user
            self.user_states[user.id] = {
                "data": {},
                "action": "delete_col"
            }
            self.reply_to(message, "Пожалуйста, введите название колонки, которую хотите удалить.")

        @self.message_handler(commands=['renamecol'])
        def rename_col(message):
            user = message.from_user
            self.user_states[user.id] = {
                "step": next(iter(RENAME_COL_NEXT_STEP)),
                "data": {},
                "action": "rename_col",
                "next_question_exists": True
            }
            self.reply_to(message, RENAME_COL_PROMPTS[self.user_states[user.id]["step"]])

        @self.message_handler(commands=['find'])
        def find(message):
            user = message.from_user
            self.user_states[user.id] = {
                "step": next(iter(SEARCHING_NEXT_STEP)),
                "data": {},
                "action": "find",
                "next_question_exists": True
            }
            self.reply_to(message, SEARCHING_PROMPTS[self.user_states[user.id]["step"]])

        @self.message_handler(func=lambda message: message.from_user.id in self.user_states)
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
                    if not message.text.isdigit():
                        self.reply_to(message, "Пожалуйста, введите число.")
                        return
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

            # --- ACTION == ADD NEWCOL ---
            if action == 'add_newcol':
                if step == "name":
                    data["name"] = message.text
                elif step == 'type':
                    data["type"] = message.text
                elif step == 'constraints':
                    data["constraints"] = message.text

                next_step: Optional[str] = self.next_step(step=step, next_step_list=NEWCOL_NEXT_STEP)
                self.user_states[user.id]['step'] = next_step
                self.user_states[user.id]["next_question_exists"] = True if next_step else False

                if not next_step:
                    self.complete_answering(user=user, data=data, message=message, context=action)
                else:
                    self.sending_next_question(message=message, prompt=NEWCOL_PROMPTS, next_step=next_step,
                                               context=action)

            # --- ACTION == DELETE COL ---
            if action == 'delete_col':
                data["name"] = message.text
                self.complete_answering(user=user, data=data, message=message, context=action)

            # --- ACTION == RENAME COL ---
            if action == 'rename_col':
                if step == "old_name":
                    data["old_name"] = message.text
                elif step == 'new_name':
                    data["new_name"] = message.text

                next_step: Optional[str] = self.next_step(step=step, next_step_list=RENAME_COL_NEXT_STEP)
                self.user_states[user.id]['step'] = next_step
                self.user_states[user.id]["next_question_exists"] = True if next_step else False

                if not next_step:
                    self.complete_answering(user=user, data=data, message=message, context=action)
                else:
                    self.sending_next_question(message=message, prompt=RENAME_COL_PROMPTS, next_step=next_step,
                                               context=action)

            # --- ACTION == FIND ---
            if action == 'find':
                if step == "colname":
                    data["colname"] = message.text
                elif step == 'value':
                    data["value"] = message.text

                next_step: Optional[str] = self.next_step(step=step, next_step_list=SEARCHING_NEXT_STEP)
                self.user_states[user.id]['step'] = next_step
                self.user_states[user.id]["next_question_exists"] = True if next_step else False

                if not next_step:
                    self.complete_answering(user=user, data=data, message=message, context=action)
                else:
                    self.sending_next_question(message=message, prompt=SEARCHING_PROMPTS, next_step=next_step,
                                               context=action)

        # @self.callback_query_handler(func=lambda c: c.data == "skip")
        # def handle_skip(callback):
        #
        #     user = callback.from_user
        #
        #     if user.id not in self.user_states:
        #         self.answer_callback_query(callback_query_id=callback.id)
        #         return
        #
        #     state: dict = self.user_states[user.id]
        #     step: str = state["step"]
        #     state["data"][step] = None  # т.к. пользователь нажал пропустить
        #
        #     # переход к следующему шагу
        #     self.handle_add_steps(callback.message)
        #
        #     self.answer_callback_query(callback.id)
