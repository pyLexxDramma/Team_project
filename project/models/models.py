from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, TEXT
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Users(Base):
    """Модель пользователя бота."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, unique=True, nullable=False)
    first_name = Column(String(length=20), nullable=False)
    age = Column(Integer)
    sex = Column(String(length=10))
    city = Column(String)

    favorites = relationship("FavouriteUsers", back_populates="user", cascade="all, delete-orphan",
                             passive_deletes=True)
    blacklists = relationship("Blacklist", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    access_tokens = relationship("AccessTokenUser", back_populates="user", cascade="all, delete-orphan",
                                 passive_deletes=True)

    def __str__(self):
        return f'User {self.id}: {self.vk_id}, {self.first_name}, {self.age}, {self.sex}, {self.city}'


class FavouriteUsers(Base):
    """Модель избранных пользователей."""
    __tablename__ = 'favourite_users'

    id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, nullable=False)
    first_name = Column(String(length=20), nullable=False)
    last_name = Column(String(length=20), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)

    user = relationship("Users", back_populates="favorites")
    photos = relationship("Photos", back_populates="favourite_user", cascade="all, delete-orphan", passive_deletes=True)

    def __str__(self):
        return (f'FavouriteUsers {self.id}: {self.vk_id}, {self.first_name},/n'
                f'{self.last_name}, {self.user_id}')


class Photos(Base):
    """Модель фотографий избранных пользователей."""
    __tablename__ = 'photos'

    id = Column(Integer, primary_key=True)
    photo_url = Column(String, unique=True, nullable=False)
    favourite_user_id = Column(Integer, ForeignKey('favourite_users.id', ondelete="CASCADE"), nullable=False)

    favourite_user = relationship("FavouriteUsers", back_populates="photos")

    def __str__(self):
        return f'Photos {self.id}: {self.photo_url}, {self.favourite_user_id}'


class Blacklist(Base):
    """Модель черного списка пользователей."""
    __tablename__ = 'blacklist'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    vk_id_to_blacklist = Column(Integer, unique=True, nullable=False)

    user = relationship("Users", back_populates="blacklists")

    def __str__(self):
        return f'Blacklist {self.id}: {self.user_id}, {self.vk_id_to_blacklist}'


class AccessTokenUser(Base):
    """Модель для хранения access token пользователей"""

    __tablename__ = 'access_token'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"))  # Исправленный внешний ключ
    access_token = Column(TEXT, unique=True)
    data_time = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("Users", back_populates="access_tokens")