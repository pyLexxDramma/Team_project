import logging
import psycopg2
from models import Users, FavouriteUsers, Photos, Blacklist
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from sqlalchemy import create_engine
from config import *
from models import *
import sqlalchemy
from psycopg2 import Error

# load_dotenv()

def connect_db():
    """
    Подключается к базе данных PostgreSQL используя SQLAlchemy.
    Returns:
        sqlalchemy.engine.Engine: Объект движка SQLAlchemy или None в случае ошибки.
    """
    try:
        conn = create_engine(DSN)
        logging.info(f"Подключено к базе {DB_NAME} на {DB_HOST}")
        return conn
    
    except SQLAlchemyError as e:
        logging.error(f"Ошибка подключения к базе данных: {e}")
        return None

def create_tables(conn):
    """Создает все таблицы в базе данных.
    Args:
        conn: Объект движка SQLAlchemy
    Note:
        Перед созданием таблиц удаляет все существующие таблицы.
    """
    try: 
        # Base.metadata.drop_all(conn)
        Base.metadata.create_all(conn)
        logging.info("Таблицы успешно созданы")
        
    except SQLAlchemyError  as e:
        logging.error(f"Ошибка при создании таблиц: {e}")

def init_db():
    """Инициализирует и возвращает сессию для работы с базой данных.
    Returns:
        Session: Объект сессии SQLAlchemy
    Raises:
        Exception: В случае ошибки соединения выводит сообщение в консоль
    """
    try:
        engine = sqlalchemy.create_engine(DSN)
        Session = sessionmaker(bind=engine)
        session = Session()
        return session
    
    except Exception:
        print ('Ошибка соединения')

def add_user(vk_id, first_name, age, sex, city):
    """Добавляет пользователя в базу данных.
    Args:
        vk_id (int): ID пользователя ВКонтакте
        first_name (str): Имя пользователя
        age (int): Возраст пользователя
        sex (int): Пол пользователя (1 - женский, 2 - мужской)
        city (str): Город пользователя
    Returns:
        str: Сообщение о результате операции
    """
    try:
        with init_db() as session:
            session.add(Users(vk_id=vk_id, first_name=first_name, age=age, sex=sex, city=city))
            session.commit()
            session.close()
            return ('Пользователь добавлен в БД')
    except SQLAlchemyError  as e:
        logging.error(f"Ошибка при добавлении пользователя {e}")

def get_user_vk_id(user_id):
    try:
        with init_db() as session:
            user = session.query(Users).filter_by(id=user_id).first()
            if user:
                return user.vk_id
            return None
    except SQLAlchemyError as e:
        logging.error(f"Ошибка при получении vk_id пользователя {user_id}: {str(e)}")
        raise

def add_favourite(vk_id, first_name, last_name, user_id):
    """Добавляет пользователя в список избранных.
        Args:
        vk_id (int): ID пользователя ВКонтакте для добавления в избранное
        first_name (str): Имя пользователя
        last_name (str): Фамилия пользователя
        user_id (int): ID пользователя бота, который добавляет в избранное
    Returns:
        str: Сообщение о результате операции
    """
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

def add_photo(photo_url, favourite_user_id):
    """Добавляет ссылку на фото для пользователя из избранного.
    Args:
        photo_url (str): URL фотографии
        favourite_user_id (int): ID пользователя из таблицы избранных
    Returns:
        str: Сообщение о результате операции
    """
    try:
        with init_db() as session:
            session.add(Photos(photo_url=photo_url, favourite_user_id=favourite_user_id))
            session.commit()
            session.close()
            return ('Фото добавлено')
    except Exception:
        return ('Ошибка при добавлении фото')

def add_blacklist(user_id, vk_id_to_blacklist):
    """Добавляет пользователя в черный список.
    Args:
        user_id (int): ID пользователя бота, который добавляет в черный список
        vk_id_to_blacklist (int): ID пользователя ВКонтакте для добавления в черный список
    Returns:
        str: Сообщение о результате операции
    """
    try:
        with init_db() as session:
            user_to_blacklist = Blacklist(user_id=user_id, vk_id_to_blacklist=vk_id_to_blacklist)
            session.add(user_to_blacklist)
            session.commit()
            session.close()
            return ('Пользователь добавлен в чёрный список')
    except Exception:
        return ('Ошибка при добавлении в чёрный список')

def get_favourite(vk_id):
    """Получает список избранных пользователей для указанного пользователя бота.
    Args:
        vk_id (int): ID пользователя ВКонтакте
    Returns:
        list: Список кортежей с информацией об избранных (имя, фамилия, vk_id)
        или сообщение об ошибке
    """
    try:
        with init_db() as session:
            data = session.query(FavouriteUsers.first_name, FavouriteUsers.last_name, FavouriteUsers.vk_id).\
                join(Users, Users.id == FavouriteUsers.user_id).\
                filter(Users.vk_id == vk_id).all()
            return data
            session.close()
    except Exception:
        return ('Ошибка при выводе списка избранных')

def get_photo(vk_id):
    """Получает фотографии избранного пользователя.
    Args:
        vk_id (int): ID пользователя ВКонтакте из списка избранных
    Returns:
        list: Список URL фотографий или сообщение об ошибке
    """
    try:
        with init_db() as session:
            photos = session.query(Photos.photo_url).join(FavouriteUsers, FavouriteUsers.id == Photos.favourite_user_id).\
                filter(FavouriteUsers.vk_id == vk_id).all()
            return photos
            session.close()
    except Exception:
        return ('Ошибка при фото избранных')

def get_blacklist(vk_id):
    """Получает черный список пользователя бота.
    Args:
        vk_id (int): ID пользователя ВКонтакте
    Returns:
        list: Список ID пользователей в черном списке или сообщение об ошибке
    """
    try:
        with init_db() as session:
            blacklist = session.query(Blacklist.vk_id_to_blacklist).join(Users, Users.id == Blacklist.user_id).\
                filter(Users.vk_id == vk_id).all()
            return blacklist
        session.close()
    except Exception:
        return ('Ошибка при выводе чёрного списка')

