import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Users(Base):
    __tablename__ = 'users'

    id = sq.Column(sq.Integer, primary_key=True)
    vk_id = sq.Column(sq.Integer, unique=True, nullable=False)
    first_name = sq.Column(sq.String(length=20), nullable=False)
    age = sq.Column(sq.Integer, nullable=False)
    sex = sq.Column(sq.String(length=10), nullable=False)
    city = sq.Column(sq.String, nullable=False)

    def __str__(self):
        return f'User {self.id}: {self.vk_id}, {self.first_name}, {self.age}, {self.sex}, {self.city}'


class FavouriteUsers(Base):
    __tablename__ = 'favourite_users'

    id = sq.Column(sq.Integer, primary_key=True)
    vk_id = sq.Column(sq.Integer, nullable=False)
    first_name = sq.Column(sq.String(length=20), nullable=False)
    last_name = sq.Column(sq.String(length=20), nullable=False)
    user_id = sq.Column(sq.Integer, sq.ForeignKey('users.id'), nullable=False)


    def __str__(self):
        return (f'FavouriteUsers {self.id}: {self.vk_id}, {self.first_name},/n'
                f'{self.last_name}, {self.user_id}')


class Photos(Base):
    __tablename__ = 'photos'

    id = sq.Column(sq.Integer, primary_key=True)
    photo_url = sq.Column(sq.String, unique=True, nullable=False)
    favourite_user_id = sq.Column(sq.Integer, sq.ForeignKey('favourite_users.id'), nullable=False)

    favourite_users = relationship(FavouriteUsers, backref='fav_us_id', cascade='all, delete')

    def __str__(self):
        return f'Photos {self.id}: {self.photo_url}, {self.favourite_user_id}'


class Blacklist(Base):
    __tablename__ = 'blacklist'

    id = sq.Column(sq.Integer, primary_key=True)
    user_id = sq.Column(sq.Integer, sq.ForeignKey('users.id'), nullable=False)
    vk_id_to_blacklist = sq.Column(sq.Integer, unique=True, nullable=False)

    users = relationship(Users, backref='id_users', cascade='all, delete')

    def __str__(self):
        return f'Blacklist {self.id}: {self.user_id}, {self.vk_id_to_blacklist}'


def create_tables(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)