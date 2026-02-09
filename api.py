import config
import re
import telebot
from typing import Optional
from datetime import date
from gui import Keyboard, STEP_KEYBOARDS
from database import MyPostgresConnection

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
    "label": "type",
    "type": "required",
    "required": "unique",
    "unique": "default_choice",
    "default_choice": "default_value",
    "default_value": None
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
    "label": "Введите название кастомного поля (например: 'Цвет', 'Дата покупки'):",
    "type": "Выберите тип значений:",
    "required": "Поле обязательное?",
    "unique": "Значение должно быть уникальным?",
    "default_choice": "Задаём значение по умолчанию?",
    "default_value": "Введите значение по умолчанию:"
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

    def _slugify_key(self, label: str) -> str:
        # очень простой slug: латиница/цифры/_
        s = label.strip().lower()
        s = re.sub(pattern=r"\s+", repl="_", string=s)
        s = re.sub(pattern=r"[^a-z0-9_]", repl="", string=s)

        if not s:
            s = "field"

        # подрежем длину
        s = s[:32]

        return s

    def _parse_typed_value(self, field_type: str, raw: str | None):
        if raw is None:
            return None, None

        raw = str(raw).strip()

        if field_type == "text":
            return raw, None

        if field_type == "int":
            if not raw.isdigit():
                return None, "Введите целое число."
            return int(raw), None

        if field_type == "float":
            raw2 = raw.replace(",", ".")
            try:
                return float(raw2), None
            except ValueError:
                return None, "Введите число (например 12.5)."

        if field_type == "bool":
            if raw.lower() in {"true", "да", "yes", "1"}:
                return True, None
            if raw.lower() in {"false", "нет", "no", "0"}:
                return False, None
            return None, "Выберите Да/Нет кнопкой."

        if field_type == "date":
            # ожидаем YYYY-MM-DD
            try:
                y, m, d = raw.split("-")
                return date(int(y), int(m), int(d)).isoformat(), None
            except Exception:
                return None, "Введите дату в формате YYYY-MM-DD."

        return None, "Неизвестный тип поля."

    def _next_step_newcol(self, current_step: str, data: dict) -> str | None:
        nxt = NEWCOL_NEXT_STEP.get(current_step)

        # если default_choice == skip, пропускаем default_value
        if current_step == "default_choice" and data.get("default") is None:
            # после default_choice(skip) завершаем
            # if data.get("type") == "text":
            #     return "max_len"
            return None

        # если default_choice == set — идём на default_value
        if current_step == "default_choice" and "default" not in data:
            return "default_value"

        # после default_value: если text — max_len, иначе конец
        if current_step == "default_value":
            if data.get("type") == "text":
                return "max_len"
            return None

        # max_len только для text
        if nxt == "max_len" and data.get("type") != "text":
            return None

        return nxt

    def build_custom_field_json(self, data: dict) -> dict:
        return {
            "key": data["key"],
            "label": data["label"],
            "type": data["type"],
            "required": bool(data.get("required", False)),
            "unique": bool(data.get("unique", False)),
            "default": data.get("default", None),
            "constraints": data.get("constraints", {}),
            "ui": data.get("ui", {})
        }

    def _reply(self, user_id: int, text: str, message=None):
        if message:
            self.reply_to(message, text)
        else:
            self.send_message(user_id, text)

    def complete_answering(self, user_id: int, context: str, data: dict, message=None):
        ''' если шагов больше нет, сохраняем в БД '''
        # if self.user_states[user.id].get("next_question_exists") is False or None:
        from homemanager import HomeManager

        if context == 'add':
            text = HomeManager().add_new_item(user_id=user_id, item_data=data)
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
        del self.user_states[user_id]  # возможно лучше pop вместе del

        # отправляем финальное сообщение
        self._reply(user_id, text, message)
        return

    def next_step(self, step: str, next_step_list: dict) -> Optional[str]:
        ''' определяем следующий шаг '''
        return next_step_list.get(step)

    def sending_next_question(self, message: telebot.types.Message, prompt: dict, next_step: str, context: str):
        ''' отправляем следующий вопрос '''
        prompt = prompt.get(next_step)
        if context == 'add':
            if next_step in SKIP_STEPS:
                # добавляем кнопку "Пропустить" для опциональных шагов
                self.reply_to(message=message, text=prompt, reply_markup=Keyboard().skip_button())
            else:
                # набор inline кнопок выбора + кнопка "Пропустить"
                self.reply_to(message=message, text=prompt)
                # self.reply_to(message=message, text=prompt, reply_markup=Keyboard().multi_inline(TYPE_BUTTONS))

        elif context == 'add_newcol':
            buttons = STEP_KEYBOARDS.get(next_step)

            if buttons:
                if buttons in SKIP_STEPS:
                    markup = Keyboard().multi_inline(buttons)
                else:
                    markup = Keyboard().multi_inline(buttons).skip_button()
                self.reply_to(message=message, text=prompt, reply_markup=markup)
            else:
                self.reply_to(message=message, text="oink")

        elif context == 'delete_col':
            from homemanager import HomeManager
            cols = HomeManager().list_custom_cols()

            if not cols:
                self.reply_to(message=message, text="Нет колонок для удаления.")
                return

            markup = Keyboard().columns_buttons(cols)

            self.reply_to(message=message, text=prompt, reply_markup=markup)
            return

        elif context == 'rename_col':
            # на шаге old_name показываем кнопки, на new_name — обычный текст
            if next_step == "old_name":
                from homemanager import HomeManager
                cols = HomeManager().list_custom_cols()  # кастомные колонки

                if not cols:
                    self.reply_to(message=message, text="Нет колонок для переименования.")
                    return

                markup = Keyboard().rename_columns_buttons(cols)
                self.reply_to(message=message, text=prompt, reply_markup=markup)
                return

            # шаг new_name — просто попросить ввести текст
            self.reply_to(message=message, text=prompt)
            return

        else:
            self.reply_to(message=message, text=prompt)

    def _process_step(self, user_id: int, text: str | None = None, step_override=None, value_override=None, message=None):

        if user_id not in self.user_states:
            return  # пользователь не в режиме добавления

        state: dict = self.user_states[user_id]
        step = step_override or state.get("step")
        data = state.get("data")
        action = state.get("action")

        # --- определяем skip ---
        is_skip = (value_override == "__skip__")

        # --- вычисляем значение ---
        if is_skip:
            value = None
        else:
            value = value_override if value_override is not None else text

        # START SCREEN for delete_col (чтобы sending_next_question вызывался из _process_step)
        if action == "delete_col" and value_override is None and text is None:
            # первый заход — просто показываем кнопки выбора
            self.sending_next_question(
                message=message,
                prompt={"name": "Выберите колонку для удаления:"},
                next_step="name",
                context="delete_col"
            )
            return

        # --- ACTION == ADD ---
        if action == 'add':
            # --- сохраняем текст пользователя в data ---
            if step == "name":
                data["name"] = value
            elif step == "brand":
                data["brand"] = value
            elif step == "model":
                data["model"] = value
            elif step == "category":
                data["category"] = value
            elif step == "quantity":
                if value_override is None:
                    if not value or not value.isdigit():
                        self._reply(user_id, "Пожалуйста, введите число.", message)
                        return

                    data["quantity"] = int(value)
                else:
                    self._reply(user_id, "Количество нельзя пропустить.", message)
                    return
            elif step == "storage_place":
                data["storage_place"] = value
            elif step == "belong_to":
                data["belong_to"] = value

            # --- определяем следующий шаг ---
            next_step = self.next_step(step=step, next_step_list=ADD_NEXT_STEP)
            self.user_states[user_id]['step'] = next_step
            self.user_states[user_id]["next_question_exists"] = True if next_step else False

            if not next_step:
                # --- если шагов больше нет, сохраняем в БД ---
                self.complete_answering(user_id=user_id, data=data, context=action, message=message)
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
            self.user_states[user_id]['step'] = next_step
            self.user_states[user_id]["next_question_exists"] = True if next_step else False

            if not next_step:
                self.complete_answering(user_id=user_id, data=data, message=message, context=action)
            elif action == 'remove':
                self.sending_next_question(message=message, prompt=REMOVE_PROMPTS, next_step=next_step,
                                           context=action)
            else:
                self.sending_next_question(message=message, prompt=ADD_MORE_PROMPTS, next_step=next_step,
                                           context=action)

        # --- ACTION == DELETE ---
        if action == 'delete':
            data["name"] = message.text
            self.complete_answering(user_id=user_id, data=data, message=message, context=action)

        # --- ACTION == ADD NEWCOL ---
        if action == 'add_newcol':
            # 1) label -> key
            if step == "label":
                if not value:
                    self._reply(user_id, "Введите название поля текстом.", message)
                    return

                label = value.strip()
                key = self._slugify_key(label)

                data["label"] = label
                data["key"] = key

            elif step == "type":
                data["type"] = value

            elif step == "required":
                data["required"] = (value == "true")

            elif step == "unique":
                # минимальная защита: unique только для text/int/date (например)
                if value == "true" and data.get("type") not in {"text", "int", "date"}:
                    self._reply(user_id, "Уникальность доступна только для text/int/date.", message)
                    return
                data["unique"] = (value == "true")

            elif step == "default_choice":
                if value == "skip":
                    data["default"] = None
                    # пропускаем default_value
                    # и, если type != text, сразу завершаем или идём дальше по flow
                elif value == "set":
                    # следующий шаг попросит default_value
                    pass
                else:
                    self._reply(user_id, "Выберите вариант кнопкой.", message)
                    return

            elif step == "default_value":
                # default_value приходит текстом
                # здесь парсим по type
                parsed, err = self._parse_typed_value(data.get("type"), value)
                if err:
                    self._reply(user_id, err, message)
                    return
                data["default"] = parsed

            elif step == "max_len":
                # только для text
                if data.get("type") != "text":
                    # если не text — этот шаг вообще не нужен
                    pass
                else:
                    if value == "none":
                        data.setdefault("constraints", {})["max_len"] = None
                    else:
                        data.setdefault("constraints", {})["max_len"] = int(value)

            # --- определить следующий шаг с учётом условных пропусков ---
            next_step = self._next_step_newcol(step, data)

            self.user_states[user_id]["step"] = next_step

            if not next_step:
                field_json = self.build_custom_field_json(data)
                # тут сохраняем в БД метаданные поля
                # HomeManager().add_newcol_meta(user_id, field_json)
                self.complete_answering(user_id=user_id, context="add_newcol", data={"field": field_json},
                                        message=message)
                return

            # отправить следующий вопрос
            self.sending_next_question(
                message=message,
                prompt=NEWCOL_PROMPTS,
                next_step=next_step,
                context=action
            )

        # --- ACTION == DELETE COL ---
        if action == "delete_col":
            # если пришло текстом — не принимаем, повторяем кнопки
            if value_override is None:
                self.sending_next_question(
                    message=message,
                    prompt={"name": "Пожалуйста, выберите колонку кнопкой:"},
                    next_step="name",
                    context="delete_col"
                )
                return

            # пришло из callback deletecol:<name>
            if not value:
                self._reply(user_id, "Выберите колонку кнопкой.", message)
                return

            data["name"] = value
            self.complete_answering(user_id=user_id, context="delete_col", data=data, message=message)
            return

        # --- ACTION == RENAME COL ---
        if action == 'rename_col':

            # old_name выбираем кнопкой (callback -> value_override)
            if step == "old_name":
                if value_override is None:
                    # если юзер пытается ввести руками — заставляем выбирать кнопкой
                    self._reply(user_id, "Пожалуйста, выберите колонку кнопкой.", message)
                    self.sending_next_question(
                        message=message,
                        prompt=RENAME_COL_PROMPTS,
                        next_step="old_name",
                        context=action
                    )
                    return

                data["old_name"] = value_override

            # new_name вводим текстом
            elif step == "new_name":
                if not value:
                    self._reply(user_id, "Введите новое имя колонки текстом.", message)
                    return

                data["new_name"] = value

            # определить следующий шаг
            next_step: Optional[str] = self.next_step(step=step, next_step_list=RENAME_COL_NEXT_STEP)
            self.user_states[user_id]['step'] = next_step
            self.user_states[user_id]["next_question_exists"] = True if next_step else False

            if not next_step:
                self.complete_answering(user_id=user_id, data=data, message=message, context=action)
            else:
                self.sending_next_question(
                    message=message,
                    prompt=RENAME_COL_PROMPTS,
                    next_step=next_step,
                    context=action
                )

            return

        # --- ACTION == FIND ---
        if action == 'find':
            if step == "colname":
                data["colname"] = message.text
            elif step == 'value':
                data["value"] = message.text

            next_step: Optional[str] = self.next_step(step=step, next_step_list=SEARCHING_NEXT_STEP)
            self.user_states[user_id]['step'] = next_step
            self.user_states[user_id]["next_question_exists"] = True if next_step else False

            if not next_step:
                self.complete_answering(user_id=user_id, data=data, message=message, context=action)
            else:
                self.sending_next_question(message=message, prompt=SEARCHING_PROMPTS, next_step=next_step,
                                           context=action)

    def register_handlers(self):
        @self.message_handler(commands=['start'])  # хэндлер команды старт
        def start(message):
            user = message.from_user
            from homemanager import HomeManager
            text = HomeManager().handle_start(user)
            self.reply_to(message, text, parse_mode="Markdown")

        @self.message_handler(commands=['view'])
        def view(message):
            user = message.from_user
            from homemanager import HomeManager
            text = HomeManager().view(user.id)
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
                "step": "name",
                "data": {},
                "action": "delete_col"
            }
            self._process_step(user_id=user.id, message=message)
            # self.reply_to(message, "Пожалуйста, введите название колонки, которую хотите удалить.")

        @self.message_handler(commands=['renamecol'])
        def rename_col(message):
            user = message.from_user
            self.user_states[user.id] = {
                "step": "old_name",
                "data": {},
                "action": "rename_col"
            }

            self.sending_next_question(
                message=message,
                prompt=RENAME_COL_PROMPTS,
                next_step="old_name",
                context="rename_col"
            )

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
            self._process_step(user_id=message.from_user.id, text=message.text, message=message)

        @self.callback_query_handler(func=lambda c: True)
        def handle_callbacks(callback):

            if callback.from_user.id not in self.user_states:
                self.answer_callback_query(callback_query_id=callback.id)
                return

            data: str = callback.data

            # state: dict = self.user_states[user_bot.id]
            # step: str = state["step"]
            # state["data"][step] = None  # т.к. пользователь нажал пропустить

            if data == 'skip':
                step = self.user_states[callback.from_user.id]["step"]

            # переход к следующему шагу
                self._process_step(user_id=callback.from_user.id, step_override=step, value_override="__skip__", message=callback.message)

                self.answer_callback_query(callback.id)
                return

            if data.startswith("deletecol:"):
                colname = data.split(":", 1)[1]

                self._process_step(
                    user_id=callback.from_user.id,
                    step_override="name",
                    value_override=colname,
                    message=callback.message
                )

                self.answer_callback_query(callback.id)
                return

            if data.startswith("renamecol:"):
                old_name = data.split(":", 1)[1]

                self._process_step(
                    user_id=callback.from_user.id,
                    step_override="old_name",
                    value_override=old_name,
                    message=callback.message
                )

                self.answer_callback_query(callback.id)
                return

            step, value = data.split(":", maxsplit=1)

            self._process_step(user_id=callback.from_user.id, step_override=step, value_override=value,
                               message=callback.message)

            self.answer_callback_query(callback.id)