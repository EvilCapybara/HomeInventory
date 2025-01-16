from sqlalchemy import String, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, declarative_base
from typing import Optional


Base = declarative_base()


class AllHouseholdItems(Base):
    __tablename__ = 'AllHouseholdItems'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    brand: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=True)
    quantity: Mapped[int] = mapped_column(SmallInteger)
    storage_place: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    belong_to: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # def __repr__(self):
    #     return f'<Main table {self.__tablename__} containing all household items>'
