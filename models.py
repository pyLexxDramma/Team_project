from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, TEXT
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()

class Users(Base):
    """Модель пользователя бота.
    Attributes:
        id (int): Первичный ключ
        vk_id (int): Уникальный ID пользователя ВКонтакте
        first_name (str): Имя пользователя (макс. 20 символов)
        age (int): Возраст пользователя
        sex (str): Пол пользователя (макс. 10 символов)
        city (str): Город пользователя
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, unique=True, nullable=False)
    first_name = Column(String(length=20), nullable=False)
    age = Column(Integer)
    sex = Column(String(length=10))
    city = Column(String)
    
    favorites = relationship("FavouriteUsers", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    blacklists = relationship("Blacklist", back_populates="user",  cascade="all, delete-orphan", passive_deletes=True)
    
    def __str__(self):
        """Строковое представление пользователя.
            Returns:
                str: Форматированная строка с данными пользователя
        """
        return f'User {self.id}: {self.vk_id}, {self.first_name}, {self.age}, {self.sex}, {self.city}'

class FavouriteUsers(Base):
    """Модель избранных пользователей.
    Attributes:
        id (int): Первичный ключ
        vk_id (int): ID пользователя ВКонтакте
        first_name (str): Имя пользователя (макс. 20 символов)
        last_name (str): Фамилия пользователя (макс. 20 символов)
        user_id (int): Внешний ключ к таблице users
    """
    __tablename__ = 'favourite_users'

    id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, nullable=False)
    first_name = Column(String(length=20), nullable=False)
    last_name = Column(String(length=20), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    
    user = relationship("Users", back_populates="favorites", cascade="all, delete")
    photos = relationship("Photos", back_populates="favourite_user",  cascade="all, delete-orphan", passive_deletes=True)

    def __str__(self):
        """Строковое представление избранного пользователя.
        Returns:
            str: Форматированная строка с данными избранного пользователя
        """
        return (f'FavouriteUsers {self.id}: {self.vk_id}, {self.first_name},/n'
                f'{self.last_name}, {self.user_id}')

class Photos(Base):
    """Модель фотографий избранных пользователей.
    Attributes:
        id (int): Первичный ключ
        photo_url (str): Уникальный URL фотографии
        favourite_user_id (int): Внешний ключ к таблице favourite_users
    Relationships:
        favourite_users: Связь один-ко-многим с FavouriteUsers (каскадное удаление)
    """
    __tablename__ = 'photos'

    id = Column(Integer, primary_key=True)
    photo_url = Column(String, unique=True, nullable=False)
    favourite_user_id = Column(Integer, ForeignKey('favourite_users.id', ondelete="CASCADE"), nullable=False)
   
    favourite_user = relationship("FavouriteUsers", back_populates="photos")

    def __str__(self):
        """Строковое представление фотографии.
        Returns:
            str: Форматированная строка с данными фотографии
        """
        return f'Photos {self.id}: {self.photo_url}, {self.favourite_user_id}'

class Blacklist(Base):
    """Модель черного списка пользователей.
    Attributes:
        id (int): Первичный ключ
        user_id (int): Внешний ключ к таблице users
        vk_id_to_blacklist (int): Уникальный ID пользователя ВКонтакте в черном списке
    Relationships:
        users: Связь один-ко-многим с Users (каскадное удаление)
    """
    __tablename__ = 'blacklist'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    vk_id_to_blacklist = Column(Integer, unique=True, nullable=False)
    
    user = relationship("Users", back_populates="blacklists")

    def __str__(self):
        """Строковое представление записи в черном списке.
        Returns:
            str: Форматированная строка с данными записи
        """
        return f'Blacklist {self.id}: {self.user_id}, {self.vk_id_to_blacklist}'
    
class AccessTokenUser(Base):
    """Модель для хранения access token пользователей"""
    
    __tablename__ = 'access_token'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.vk_id', ondelete="CASCADE"))
    access_token = Column(TEXT,unique=True)
    data_time = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    user = relationship("Users", backref="access_tokens")        
        
