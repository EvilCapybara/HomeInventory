import redis
import rq
from rq import exceptions
from sqlalchemy import select, case, event, String, SmallInteger, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, declarative_base, relationship
from tasks import redis_conn, task_queue, export_inventory_table
from datetime import datetime, timezone
# from elastic import add_to_index, remove_from_index, query_index
from typing import Optional


Base = declarative_base()


# class SearchableMixin(object):
#     @classmethod
#     def search(cls, expression, connection):
#         ids, total = query_index('AllHouseholdItems', expression)  # FIXME заменить хардкод на cls.__tablename__
#         if total == 0:
#             return [], 0
#         when = []
#         for i in range(len(ids)):
#             when.append((ids[i], i))
#         query = select(cls).where(cls.id.in_(ids)).order_by(case(*when, value=cls.id))
#         return connection.session.scalars(query), total
#
#     @classmethod
#     def before_commit(cls, session):
#         session._changes = {
#             'add': list(session.new),
#             'update': list(session.dirty),
#             'delete': list(session.deleted)
#         }
#
#     @classmethod
#     def after_commit(cls, session):
#         for obj in session._changes['add']:
#             if isinstance(obj, SearchableMixin):
#                 add_to_index(cls.__tablename__, obj)  # FIXME заменить на obj.__tablename__
#         for obj in session._changes['update']:
#             if isinstance(obj, SearchableMixin):
#                 add_to_index(cls.__tablename__, obj)
#         for obj in session._changes['delete']:
#             if isinstance(obj, SearchableMixin):
#                 remove_from_index(cls.__tablename__, obj)
#         session._changes = None
#
#     @classmethod
#     def reindex(cls, connection):
#         for obj in connection.session.scalars(select(cls)):
#             add_to_index(cls.__tablename__, obj)


class Users(Base):
    __tablename__ = 'Users'

    user_id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    first_name: Mapped[str] = mapped_column(String(64), unique=False, nullable=False)

    items: Mapped[list["AllHouseholdItems"]] = relationship(
        back_populates="user",  # <-- ссылается на поле owner_id в AllHouseholdItems
        cascade="all, delete-orphan"
    )


class AllHouseholdItems(Base):  # потом вернуть наследование от searchable mixin
    __tablename__ = 'AllHouseholdItems'
    __searchable__ = ['name', 'brand', 'category', 'storage_place']  # тип подчеркивания указывает на обработку внешними библиотеками/инструментами

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    brand: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=True)
    quantity: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    storage_place: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    belong_to: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    owner_id: Mapped[int] = mapped_column(ForeignKey('Users.user_id'), nullable=False)

    user: Mapped["Users"] = relationship("Users", back_populates="items")  # <-- ссылается на поле user_id в Users

    # def __repr__(self):
    #     return f'<Main table {self.__tablename__} containing all household items>'


# AllHouseholdItems.__bases__ = (SearchableMixin,)  # добавляем родителя поздним числом


class Task(Base):  # warranty_expiry_notifications_and_other_emails
    __tablename__ = "tasks"

    job_id: Mapped[Optional[str]] = mapped_column(String(36), primary_key=True)  # queue.enqueue(..., job_id=task.id)
    name: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[Optional[str]] = mapped_column(String(64))
    complete: Mapped[bool] = mapped_column(default=False)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.job_id, connection=redis_conn)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100

    def launch_task(self, name, description, *args, **kwargs):
        rq_job = task_queue.enqueue(f'tasks.{name}', *args, **kwargs)  # аргументы для функции задачи (у автора вторым аргументом стоит self.id)
        task = Task(job_id=rq_job.get_id(), name=name, description=description,
                    launcher=self)  # формирование объекта для своей бд с тасками
        # session.add(task)  # TODO инкапсулировать метод add smth to session в главном модуле
        return task

    def get_tasks_in_progress(self):
        query = select(Task).where(Task.complete is False)
        # return session.scalars(query)

    def get_specific_task_in_progress(self, name):
        query = select(Task).where(Task.name == name, Task.complete is False)
        # return session.scalar(query)


# def listening(session):
#     event.listen(session, 'before_commit', SearchableMixin.before_commit)
#     event.listen(session, 'after_commit', SearchableMixin.after_commit)

