import sqlalchemy
from sqlalchemy.orm import sessionmaker
import os
from sqlalchemy import exists
from sqlalchemy.exc import SQLAlchemyError
from VKinder_db.models import *
from dotenv import load_dotenv


load_dotenv()

def create_tables(engine):
    # Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

'''
Функция создание таблиц
В переменную DNS подставить путь с БД на своём компьютере, либо создать текстовый файл '.env' и записать путь туда
'''
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

'''
Создание таблиц
Создание таблиц происходит сдесь, отдельно от основного модуля программы,
чтобы данные пользователей не обнуляли при перезапуске программы
'''
create_db()

'''
Открытие сессии
'''
def init_db():
    
    try:
        DNS = os.getenv('DNS')
        engine = sqlalchemy.create_engine(DNS)
        Session = sessionmaker(bind=engine)
        session = Session()
        return session
    except SQLAlchemyError as e :
        print (f'Ошибка соединения {e}')

'''
Добавление пользователя с которым общается бот в БД
vk_id - vk_id пользователя
first_name - имя
age - возраст
sex - пол
city - город
'''
def add_user(vk_id, first_name, age, sex, city):
    try:
        with init_db() as session:
            user_exists = session.query(exists().where(Users.id == vk_id)).scalar()
            if user_exists:
                return 'Пользователь есть в БД'
            
            session.add(Users(id=vk_id, first_name=first_name, age=age, sex=sex, city=city))
            session.commit()
            session.close()
            return 'Пользователь добавлен в БД'
    except SQLAlchemyError as e:
        return f'Ошибка при добавлении пользователя {e}'

'''
Добавление токена в БД
token - токен пользователя
date - дата действия
vk_id - vk_id пользователя
'''
def add_token(token, date, vk_id):
    try:
        with init_db() as session:
            session.add(AccessToken(token=token, date=date, user_id=vk_id))
            session.commit()
            session.close()
            return 'Токен пользователь добавлен в БД'
    except SQLAlchemyError as e :
        return f'Ошибка при добавлении токена пользователя {e}'

'''
Добавление в список избранных
vk_id - vk_id пользователя, которого добавляют в избранное
first_name - имя пользователя, которого добавляют в избранное
last_name - фамилия пользователя, которого добавляют в избранное
user_id - vk_id пользователя с которым общается бот
'''
def add_favourite(vk_id, first_name, last_name, user_id):
    try:
        with init_db() as session:
            favorite_user = session.query(FavouriteUsers.id).all()
            if vk_id not in [el[0] for el in favorite_user]:
                session.add(FavouriteUsers(id=vk_id, first_name=first_name, last_name=last_name))

            favorite_list = session.query(Favourite.favourite_user_id).filter(Favourite.user_id == user_id).all()
            if vk_id not in [el[0] for el in favorite_list]:
                session.add(Favourite(user_id=user_id, favourite_user_id=vk_id))
                session.commit()
                session.close()
    except SQLAlchemyError as e :
        return (f'Ошибка при добавлении в избранное {e}')

'''
Добавление ссылок на фото. При сохранении профиля в избранное, программа добавляет самые популярные фото к нему.
Каждому профилю из списка  избранное соответствует уникальная url на фото (одна или несколько).
photo_url - ссылка на фото
favourite_user_id - vk_id профиля избранного
'''
def add_photo(photo_url, favourite_user_id):
    try:
        with init_db() as session:
            session.add(Photos(photo_url=photo_url, favourite_user_id=favourite_user_id))
            session.commit()
            session.close()
            return ('Фото добавлено')
    except SQLAlchemyError as e:
        return (f'Ошибка при добавлении фото {e}')

'''
Добавление в чёрный список
vk_id - vk_id пользователя, которого добавляют в чёрный список
first_name - имя пользователя, которого добавляют в чёрный список
last_name - фамилия пользователя, которого добавляют в чёрный список
user_id - vk_id пользователя с которым общается бот
'''
def add_blacklist(vk_id, first_name, last_name, user_id):
    try:
        with init_db() as session:
            blacklist_users = session.query(BlacklistUsers.id).all()
            if vk_id not in [el[0] for el in blacklist_users]:
                session.add(BlacklistUsers(id=vk_id, first_name=first_name, last_name=last_name))

            blacklist = session.query(Blacklist.blacklist_user_id).filter(Blacklist.user_id == user_id).all()
            if vk_id not in [el[0] for el in blacklist]:
                session.add(Blacklist(user_id=user_id, blacklist_user_id=vk_id))
                session.commit()
                session.close()
    except SQLAlchemyError as e:
        return (f'Ошибка при добавлении в чёрный список {e}')

'''
Получение токена и даты действия
vk_id - vk_id пользователя
'''
def get_token(vk_id):
    try:
        with init_db() as session:
            info = session.query(AccessToken.token, AccessToken.date).filter(AccessToken.user_id == vk_id).all()
            token = info[0][0]
            date = info[0][1]
            session.close()
            return f'{token}, {date}'
    except SQLAlchemyError as e:
        return (f'Ошибка при выводе токена {e}')


'''
Получение списка избранных
vk_id - vk_id пользователя с которым общается бот
'''
def get_favourite(vk_id):
    try:
        with init_db() as session:
            data = session.query(FavouriteUsers.first_name, FavouriteUsers.last_name, FavouriteUsers.id).\
                join(Favourite, Favourite.favourite_user_id == FavouriteUsers.id ).\
                join(Users, Users.id == Favourite.user_id).\
                filter(Users.id == vk_id).all()
            session.close()
            return data
    except SQLAlchemyError as e :
        return (f'Ошибка при выводе списка избранных {e}')

'''
Получение фото
vk_id - vk_id избранного пользователя
'''
def get_photo(vk_id):
    try:
        with init_db() as session:
            photos = session.query(Photos.photo_url).join(FavouriteUsers, FavouriteUsers.id == Photos.favourite_user_id).\
                filter(FavouriteUsers.id == vk_id).all()
            session.close()
            return photos
    except SQLAlchemyError as e :
        return (f'Ошибка при получении фото избранных {e}')

'''
Получение чёрного списка
vk_id - vk_id пользователя с которым общается бот
'''
def get_blacklist(vk_id):
    try:
        with init_db() as session:
            blacklist = session.query(BlacklistUsers.first_name, BlacklistUsers.last_name, BlacklistUsers.id).\
                join(Blacklist, Blacklist.blacklist_user_id == BlacklistUsers.id).\
                join(Users, Users.id == Blacklist.user_id).\
                filter(Users.id == vk_id).all()
            session.close()
            return blacklist
    except SQLAlchemyError as e:
        return (f"Ошибка при получении чёрного списка: {e}")

'''
Удаление профиля из списка избранных
vk_id - vk_id профиля в избранном
user_id - - vk_id пользователя с которым общается бот
'''
def delete_favourite(vk_id, user_id):
    try:
        with init_db() as session:
            favourite = session.query(Favourite).\
                filter(Favourite.user_id == user_id, Favourite.favourite_user_id == vk_id).first()
            if not favourite:
                return 'Пользователь не найден в списке избранных'
            session.delete(favourite)

            other_favourites = session.query(Favourite). \
                filter(Favourite.favourite_user_id == vk_id).count()
            if other_favourites == 0:
                session.query(Photos).filter(Photos.favourite_user_id == vk_id).delete()
                session.query(FavouriteUsers).filter(FavouriteUsers.id == vk_id).delete()

            session.commit()
            session.close()
            return 'Успешно, профиль удалён из списка избранного'
    except SQLAlchemyError as e :
        return (f'Ошибка при удалении из списка избранного {e}')

'''
Удаление профиля из чёрного списка
vk_id - vk_id профиля в чёрном списке
user_id - - vk_id пользователя с которым общается бот
'''
def delete_blacklist(vk_id, user_id):
    try:
        with init_db() as session:
            blacklist = session.query(Blacklist).\
                filter(Blacklist.user_id == user_id, Blacklist.blacklist_user_id == vk_id).first()
            if not blacklist:
                return 'Пользователь не найден в чёрном списке'
            session.delete(blacklist)

            other_blacklists = session.query(Blacklist).filter(Blacklist.blacklist_user_id == vk_id).count()
            if other_blacklists == 0:
                session.query(BlacklistUsers).filter(BlacklistUsers.id == vk_id).delete()

            session.commit()
            session.close()
            return 'Успешно, профиль удалён из чёрного списка'
    except SQLAlchemyError as e :
        return (f'Ошибка при удалении из чёрного списка {e}')
