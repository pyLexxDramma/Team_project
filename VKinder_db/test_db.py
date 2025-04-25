import pytest
from create_db import add_user, add_favourite, add_photo, add_blacklist, get_favourite, get_blacklist, get_photo


def generate_add_user():
    yield '547465', 'Фёдор', '30', 'мужской', 'Санкт-Петербург', 'Пользователь добавлен в БД'
    yield '547724', 'Иван', '35', 'мужской', 'Выборг', 'Пользователь добавлен в БД'
    yield '745452','Фрося', '28', 'женский', 'Петрозаводск', 'Пользователь добавлен в БД'
    yield '547724', 'Иван', '35', 'мужской', 'Выборг', 'Ошибка при добавлении пользователя'

@pytest.mark.parametrize('a,b,c,d,e,expected', generate_add_user())
def test_add_user(a, b, c, d, e, expected):
    assert add_user(a, b, c, d, e) == expected


def generate_add_favourite():
    yield 845456, 'Катя', 'Катина', '1', 'Пользователь добавлен в избранное'
    yield 959555, 'Дима', 'Димин', '1', 'Пользователь добавлен в избранное'
    yield 845456, 'Катя', 'Катина', '2', 'Пользователь добавлен в избранное'
    yield 845456, 'Катя', 'Катина', '1', 'Пользователь уже есть в избранном'

@pytest.mark.parametrize('a, b, c, d, expected', generate_add_favourite())
def test_add_favourite(a, b, c, d, expected):
    assert add_favourite(a, b, c, d) == expected


def generate_add_photo():
    yield 'https://netology.ru/_next/static/media/slide1.06c5386d.webp', 1, 'Фото добавлено'
    yield 'https://netology.ru/_next/static/media/slide1.06c5386d.webp', 1, 'Ошибка при добавлении фото'
    yield 'https://netology.ru/_next/static/media/slide1.06c5386d.webp', 2, 'Ошибка при добавлении фото'
    yield 'https://netology.ru/_next/static/media/slide4.203ea60e.webp', 1, 'Фото добавлено'
    yield 'https://netology.ru/_next/static/media/slide3.54d136f3.webp', 1, 'Фото добавлено'
    yield 'https://netology.ru/_next/static/media/slide2.95abc67e.webp', 2, 'Фото добавлено'
    yield 'https://netology.ru/_next/static/media/image_2.4c13fee0.webp', 2, 'Фото добавлено'
    yield 'https://netology.ru/_next/static/media/image_3.e1ec04f0.webp', 2, 'Фото добавлено'

@pytest.mark.parametrize('a, b, expected', generate_add_photo())
def test_add_photo(a, b, expected):
     assert add_photo(a, b) == expected


def generate_add_blacklist():
    yield '2', '5456785', 'Пользователь добавлен в чёрный список'
    yield '3', '5677451', 'Пользователь добавлен в чёрный список'
    yield '2', '5456785', 'Ошибка при добавлении в чёрный список'

@pytest.mark.parametrize('a, b, expected', generate_add_blacklist())
def test_add_blacklist(a, b, expected):
    assert add_blacklist(a, b) == expected


def generate_get_favourite():
    yield 547465, [('Катя', 'Катина', 845456), ('Дима', 'Димин', 959555)]
    yield 547724, [('Катя', 'Катина', 845456)]

@pytest.mark.parametrize('a, expected', generate_get_favourite())
def test_get_favourite(a, expected):
    assert get_favourite(a) == expected


def generate_get_photo():
    yield 845456, [('https://netology.ru/_next/static/media/slide1.06c5386d.webp',),
           ('https://netology.ru/_next/static/media/slide4.203ea60e.webp',),
           ('https://netology.ru/_next/static/media/slide3.54d136f3.webp',)]
    yield 959555, [('https://netology.ru/_next/static/media/slide2.95abc67e.webp',),
           ('https://netology.ru/_next/static/media/image_2.4c13fee0.webp',),
           ('https://netology.ru/_next/static/media/image_3.e1ec04f0.webp',)]

@pytest.mark.parametrize('a, expected', generate_get_photo())
def test_get_photo(a, expected):
    assert get_photo(a) == expected


def generate_get_blacklist():
    yield 547724, [(5456785,)]
    yield 745452, [(5677451,)]

@pytest.mark.parametrize('a, expected', generate_get_blacklist())
def test_get_blacklist(a, expected):
    assert get_blacklist(a) == expected