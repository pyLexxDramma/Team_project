import sqlalchemy as sq
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Users(Base):
    __tablename__ = 'users'

    id = sq.Column(sq.Integer, primary_key=True, nullable=False)
    first_name = sq.Column(sq.String(length=20), nullable=False)
    age = sq.Column(sq.Integer, nullable=False)
    sex = sq.Column(sq.String(length=10), nullable=False)
    city = sq.Column(sq.String, nullable=False)

    def __str__(self):
        return f'User {self.id}: {self.first_name}, {self.age}, {self.sex}, {self.city}'

class AccessToken(Base):
    __tablename__ = 'access_token'

    id = sq.Column(sq.Integer, primary_key=True, nullable=False)
    token = sq.Column(sq.Text, unique=True, nullable=False)
    date = sq.Column(sq.DateTime,default=datetime.utcnow, nullable=False)
    user_id = sq.Column(sq.Integer, ForeignKey('users.id'))

    users = relationship(Users, backref='id_users')

    def __str__(self):
        return f'AccessToken {self.id}: {self.token}, {self.user_id}, {self.date}'

class FavouriteUsers(Base):
    __tablename__ = 'favourite_users'

    id = sq.Column(sq.Integer, primary_key=True, nullable=False)
    first_name = sq.Column(sq.String(length=20), nullable=False)
    last_name = sq.Column(sq.String(length=20), nullable=False)

    def __str__(self):
        return (f'FavouriteUsers {self.id}: {self.first_name},/n'
                f'{self.last_name}')

class Favourite(Base):
    __tablename__ = 'favourite'

    id = sq.Column(sq.Integer, primary_key=True, nullable=False)
    user_id = sq.Column(sq.Integer, ForeignKey('users.id'))
    favourite_user_id = sq.Column(sq.Integer, ForeignKey('favourite_users.id'))

    users = relationship(Users, backref='us_id')
    favourite_users = relationship(FavouriteUsers, backref='favourite_us_id')

    def __str__(self):
        return f'Favourite {self.id}: {self.user_id}, {self.favourite_user_id}'


class Photos(Base):
    __tablename__ = 'photos'

    id = sq.Column(sq.Integer, primary_key=True)
    photo_url = sq.Column(sq.String, unique=True, nullable=False)
    favourite_user_id = sq.Column(sq.Integer, sq.ForeignKey('favourite_users.id'), nullable=False)

    favourite_users = relationship(FavouriteUsers, backref='fav_us_id', cascade='all, delete')

    def __str__(self):
        return f'Photos {self.id}: {self.photo_url}, {self.favourite_user_id}'


class BlacklistUsers(Base):
    __tablename__ = 'blacklist_users'

    id = sq.Column(sq.Integer, primary_key=True, nullable=False)
    first_name = sq.Column(sq.String(length=20), nullable=False)
    last_name = sq.Column(sq.String(length=20), nullable=False)

    def __str__(self):
        return f'BlacklistUsers {self.id}: {self.first_name}, {self.last_name}'


class Blacklist(Base):
    __tablename__ = 'blacklist'

    id = sq.Column(sq.Integer, primary_key=True, nullable=False)
    user_id = sq.Column(sq.Integer, sq.ForeignKey('users.id'), nullable=False)
    blacklist_user_id = sq.Column(sq.Integer, ForeignKey('blacklist_users.id'), nullable=False)

    users = relationship(Users, backref='id_user')
    blacklist_users = relationship(BlacklistUsers, backref='id_blacklist_user')

    def __str__(self):
        return f'Blacklist {self.id}: {self.user_id}, {self.blacklist_user_id}'


def create_tables(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)