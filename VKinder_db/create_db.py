import sqlalchemy
from sqlalchemy.orm import sessionmaker
import os
from models import create_tables, Users, FavouriteUsers, Photos, Blacklist
from dotenv import load_dotenv

load_dotenv()

# Функция создание таблиц
def create_db():
    try:
        DNS = os.getenv('DNS')
        engine = sqlalchemy.create_engine(DNS)
        Session = sessionmaker(bind=engine)
        session = Session()
        create_tables(engine)
        session.close()
    except Exception:
        print ('Ошибка создания БД')

# Создание таблиц
create_db()

# Открытие сессии
def init_db():
    try:
        DNS = os.getenv('DNS')
        engine = sqlalchemy.create_engine(DNS)
        Session = sessionmaker(bind=engine)
        session = Session()
        return session
    except Exception:
        print ('Ошибка соединения')

# Добавление пользователя с которым общается бот в БД
def add_user(vk_id, first_name, age, sex, city):
    try:
        with init_db() as session:
            session.add(Users(vk_id=vk_id, first_name=first_name, age=age, sex=sex, city=city))
            session.commit()
            session.close()
            return ('Пользователь добавлен в БД')
    except Exception:
        return ('Ошибка при добавлении пользователя')

# Добавление в список избранных
def add_favourite(vk_id, first_name, last_name, user_id):
    try:
        with init_db() as session:
            favorite_list = session.query(FavouriteUsers.vk_id).filter(FavouriteUsers.user_id == user_id).all()
            if vk_id not in [el[0] for el in favorite_list]:
                session.add(FavouriteUsers(vk_id=vk_id, first_name=first_name, last_name=last_name, user_id=user_id))
                session.commit()
                session.close()
                return ('Пользователь добавлен в избранное')
            else:
                return ('Пользователь уже есть в избранном')
    except Exception:
        return ('Ошибка при добавлении в избранное')

# Добавление ссылок на фото
def add_photo(photo_url, favourite_user_id):
    try:
        with init_db() as session:
            session.add(Photos(photo_url=photo_url, favourite_user_id=favourite_user_id))
            session.commit()
            session.close()
            return ('Фото добавлено')
    except Exception:
        return ('Ошибка при добавлении фото')

# Добавление в чёрный список
def add_blacklist(user_id, vk_id_to_blacklist):
    try:
        with init_db() as session:
            user_to_blacklist = Blacklist(user_id=user_id, vk_id_to_blacklist=vk_id_to_blacklist)
            session.add(user_to_blacklist)
            session.commit()
            session.close()
            return ('Пользователь добавлен в чёрный список')
    except Exception:
        return ('Ошибка при добавлении в чёрный список')

# Получение списка избранных
def get_favourite(vk_id):
    try:
        with init_db() as session:
            data = session.query(FavouriteUsers.first_name, FavouriteUsers.last_name, FavouriteUsers.vk_id).\
                join(Users, Users.id == FavouriteUsers.user_id).\
                filter(Users.vk_id == vk_id).all()
            return data
            session.close()
    except Exception:
        return ('Ошибка при выводе списка избранных')

# Получение фото по vk_id избранного пользователя
def get_photo(vk_id):
    try:
        with init_db() as session:
            photos = session.query(Photos.photo_url).join(FavouriteUsers, FavouriteUsers.id == Photos.favourite_user_id).\
                filter(FavouriteUsers.vk_id == vk_id).all()
            return photos
            session.close()
    except Exception:
        return ('Ошибка при фото избранных')

# Получение чёрного списка
def get_blacklist(vk_id):
    try:
        with init_db() as session:
            blacklist = session.query(Blacklist.vk_id_to_blacklist).join(Users, Users.id == Blacklist.user_id).\
                filter(Users.vk_id == vk_id).all()
            return blacklist
    except Exception:
        return ('Ошибка при выводе чёрного списка')

