import logging
from models import Users, FavouriteUsers, Photos, Blacklist, AccessTokenUser
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine
from config import *
from models import *
import sqlalchemy as sa

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def connect_db():
    """Подключается к базе данных PostgreSQL используя SQLAlchemy."""
    try:
        conn = create_engine(DSN)
        logging.info(f"Подключено к базе {DB_NAME} на {DB_HOST}")
        return conn

    except SQLAlchemyError as e:
        logging.error(f"Ошибка подключения к базе данных: {e}")
        return None


def create_tables(conn):
    """Создает все таблицы в базе данных."""
    try:
        # Base.metadata.drop_all(conn) # удаляет все таблицы
        Base.metadata.create_all(conn)

        #  Добавляем создание таблицы search_results
        metadata = sa.MetaData()
        search_results_table = sa.Table(
            'search_results', metadata,
            sa.Column('user_id', sa.Integer, nullable=False),
            sa.Column('target_user_id', sa.Integer, nullable=False),
            sa.Column('score', sa.Float, nullable=False),
        )
        metadata.create_all(conn)

        logging.info("Таблицы успешно созданы")

    except SQLAlchemyError as e:
        logging.error(f"Ошибка при создании таблиц: {e}")


def init_db():
    """Инициализирует и возвращает сессию для работы с базой данных."""
    try:
        engine = sa.create_engine(DSN)  # Используем sqlalchemy.create_engine
        Session = sessionmaker(bind=engine)
        return Session()

    except Exception as e:
        logging.error(f"Ошибка соединения с базой данных: {e}")  # Логируем ошибку
        raise  # Пробрасываем исключение дальше, чтобы его можно было обработать


def add_user(vk_id, first_name, age, sex, city):
    """Добавляет пользователя в базу данных."""
    try:
        session = init_db()  # Создаем сессию
        user = Users(vk_id=vk_id, first_name=first_name, age=age, sex=sex, city=city)
        session.add(user)
        session.commit()
        logging.info(f"Пользователь {vk_id} добавлен в БД")  # Логируем успешное добавление
        return 'Пользователь добавлен в БД'
    except SQLAlchemyError as e:
        logging.error(f"Ошибка при добавлении пользователя {vk_id}: {e}")  # Логируем ошибку
        session.rollback()
        return f'Ошибка при добавлении пользователя {vk_id} в БД: {e}'
    finally:
        session.close()


def add_favourite(vk_id, first_name, last_name, user_id):
    """Добавляет пользователя в список избранных."""
    try:
        session = init_db()
        favorite_list = session.query(FavouriteUsers.vk_id).filter(FavouriteUsers.user_id == user_id).all()
        if vk_id not in [el[0] for el in favorite_list]:
            favorite_user = FavouriteUsers(vk_id=vk_id, first_name=first_name, last_name=last_name, user_id=user_id)
            session.add(favorite_user)
            session.commit()
            logging.info(f"Пользователь {vk_id} добавлен в избранное для пользователя {user_id}")
            return 'Пользователь добавлен в избранное'
        else:
            return 'Пользователь уже есть в избранном'
    except SQLAlchemyError as e:
        logging.error(f"Ошибка при добавлении в избранное пользователя {vk_id} для пользователя {user_id}: {e}")
        session.rollback()
        return f'Ошибка при добавлении в избранное пользователя {vk_id}: {e}'
    finally:
        session.close()


def add_photo(photo_url, favourite_user_id):
    """Добавляет ссылку на фото для пользователя из избранного."""
    try:
        session = init_db()
        photo = Photos(photo_url=photo_url, favourite_user_id=favourite_user_id)
        session.add(photo)
        session.commit()
        logging.info(f"Фотография добавлена для пользователя из избранного с ID {favourite_user_id}")
        return 'Фото добавлено'
    except SQLAlchemyError as e:
        logging.error(f"Ошибка при добавлении фотографии для пользователя из избранного с ID {favourite_user_id}: {e}")
        session.rollback()
        return f'Ошибка при добавлении фото: {e}'
    finally:
        session.close()

    def add_blacklist(user_id, vk_id_to_blacklist):
        """Добавляет пользователя в черный список."""
        try:
            session = init_db()
            blacklist_entry = Blacklist(user_id=user_id, vk_id_to_blacklist=vk_id_to_blacklist)
            session.add(blacklist_entry)
            session.commit()
            logging.info(f"Пользователь {vk_id_to_blacklist} добавлен в черный список пользователем {user_id}")
            return 'Пользователь добавлен в чёрный список'
        except SQLAlchemyError as e:
            logging.error(
                f"Ошибка при добавлении пользователя {vk_id_to_blacklist} в черный список пользователем {user_id}: {e}")
            session.rollback()
            return f'Ошибка при добавлении в чёрный список: {e}'
        finally:
            session.close()

    def get_favourite(vk_id):
        """Получает список избранных пользователей для указанного пользователя бота."""
        try:
            session = init_db()
            data = session.query(FavouriteUsers.first_name, FavouriteUsers.last_name, FavouriteUsers.vk_id). \
                join(Users, Users.id == FavouriteUsers.user_id). \
                filter(Users.vk_id == vk_id).all()
            logging.info(f"Получен список избранных пользователей для пользователя {vk_id}")
            return data
        except SQLAlchemyError as e:
            logging.error(f"Ошибка при получении списка избранных для пользователя {vk_id}: {e}")
            return f'Ошибка при выводе списка избранных: {e}'
        finally:
            session.close()

    def get_photo(vk_id):
        """Получает фотографии избранного пользователя."""
        try:
            session = init_db()
            photos = session.query(Photos.photo_url).join(FavouriteUsers,
                                                          FavouriteUsers.id == Photos.favourite_user_id). \
                filter(FavouriteUsers.vk_id == vk_id).all()
            logging.info(f"Получены фотографии для избранного пользователя {vk_id}")
            return photos
        except SQLAlchemyError as e:
            logging.error(f"Ошибка при получении фотографий для избранного пользователя {vk_id}: {e}")
            return f'Ошибка при фото избранных: {e}'
        finally:
            session.close()

    def get_blacklist(vk_id):
        """Получает черный список пользователя бота."""
        try:
            session = init_db()
            blacklist = session.query(Blacklist.vk_id_to_blacklist) \
                .join(Users, Users.id == Blacklist.user_id) \
                .filter(Users.vk_id == vk_id).all()
            logging.info(f"Получен черный список для пользователя {vk_id}")
            return blacklist
        except SQLAlchemyError as e:
            logging.error(f"Ошибка при получении черного списка для пользователя {vk_id}: {e}")
            return f'Ошибка при выводе чёрного списка: {e}'
        finally:
            session.close()
