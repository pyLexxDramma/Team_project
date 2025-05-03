import pytest
from create_db import add_user, add_favourite, add_photo, add_blacklist, get_favourite, get_blacklist, get_photo,\
    delete_favourite, delete_blacklist, add_token, get_token


def generate_add_user():
    yield 547465, 'Фёдор', '30', 'мужской', 'Санкт-Петербург', 'Пользователь добавлен в БД'
    yield 547724, 'Иван', '35', 'мужской', 'Выборг', 'Пользователь добавлен в БД'
    yield 745455,'Фрося', '28', 'женский', 'Петрозаводск', 'Пользователь добавлен в БД'
    yield 547724, 'Иван', '35', 'мужской', 'Выборг', 'Пользователь есть в БД'

@pytest.mark.parametrize('a,b,c,d,e,expected', generate_add_user())
def test_add_user(a, b, c, d, e, expected):
    assert add_user(a, b, c, d, e) == expected

def generate_add_token():
    token = 'vk1.a.y94ZySf2OFXIYr4ja2nAFz6j37CJCBzgeqb9L_uM7qp4L2eDtKAdW0huVW4SJIMTaInlKVPPJHjo7sgjeWEnlm65nZSOlA98uO-xmGJJHNDKbyAzjP-CRVq0sy9W7U62w-xSLWqnPAsOLU9nBXrJC_4SYWOsqzRLrStx7hMm1HziPawRZRQF1w5V8Z8VzdP2rwRcptpJUOJdEkzVDO-ZTA'
    yield token, '2025-04-26 19:00:09.018862+05:00', 547465, 'Токен пользователь добавлен в БД'

@pytest.mark.parametrize('a, b, c, expected', generate_add_token())
def test_add_token(a, b, c, expected):
    assert add_token(a, b, c) == expected


def generate_add_favourite():
    yield 845456, 'Катя', 'Катина', 547465, None          # Добавится в таблицу
    yield 959555, 'Вася', 'Пупкин', 547465, None           # Добавится в таблицу
    yield 845456, 'Катя', 'Катина', 547724, None          # Добавится в таблицу
    yield 845456, 'Катя', 'Катина', 547465, None          # Не добавится в таблицу
    yield 959555, 'Вася', 'Пупкин', 745455, None          # Добавится в таблицу

@pytest.mark.parametrize('a, b, c, d, expected', generate_add_favourite())
def test_add_favourite(a, b, c, d, expected):
    assert add_favourite(a, b, c, d) == expected


def generate_add_photo():
    yield 'https://netology.ru/_next/static/media/slide1.06c5386d.webp', 845456, 'Фото добавлено'
    yield 'https://netology.ru/_next/static/media/slide1.06c5386d.webp', 845456, 'Ошибка при добавлении фото'
    yield 'https://netology.ru/_next/static/media/slide1.06c5386d.webp', 959555, 'Ошибка при добавлении фото'
    yield 'https://netology.ru/_next/static/media/slide4.203ea60e.webp', 845456, 'Фото добавлено'
    yield 'https://netology.ru/_next/static/media/slide3.54d136f3.webp', 845456, 'Фото добавлено'
    yield 'https://netology.ru/_next/static/media/slide2.95abc67e.webp', 959555, 'Фото добавлено'
    yield 'https://netology.ru/_next/static/media/image_2.4c13fee0.webp', 959555, 'Фото добавлено'
    yield 'https://netology.ru/_next/static/media/image_3.e1ec04f0.webp', 959555, 'Фото добавлено'

@pytest.mark.parametrize('a, b, expected', generate_add_photo())
def test_add_photo(a, b, expected):
     assert add_photo(a, b) == expected


def generate_add_blacklist():
    yield 547724, 'Настя', 'Настина', 547465, None           # Добавится в таблицу
    yield 745452, 'Арнольд', 'Арнольдов', 745455, None       # Добавится в таблицу
    yield 547724, 'Настя', 'Настина', 547465, None           # Не добавится в таблицу

@pytest.mark.parametrize('a, b, c, d, expected', generate_add_blacklist())
def test_add_blacklist(a, b, c, d, expected):
    assert add_blacklist(a, b, c, d) == expected


def generate_get_token():
    yield 547465, ('vk1.a.y94ZySf2OFXIYr4ja2nAFz6j37CJCBzgeqb9L_uM7qp4L2eDtKAdW0huVW4SJIMTaInlKVPPJHjo7sgjeWEnlm65nZSOlA98uO-xmGJJHNDKbyAzjP-CRVq0sy9W7U62w-xSLWqnPAsOLU9nBXrJC_4SYWOsqzRLrStx7hMm1HziPawRZRQF1w5V8Z8VzdP2rwRcptpJUOJdEkzVDO-ZTA, '
                '2025-04-26 19:00:09.018862')

@pytest.mark.parametrize('a, expected', generate_get_token())
def test_get_token(a, expected):
    assert get_token(a) == expected


def generate_get_favourite():
    yield 547465, [('Катя', 'Катина', 845456), ('Вася', 'Пупкин', 959555)]
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
    yield 547465, [('Настя', 'Настина', 547724)]
    yield 745455, [('Арнольд', 'Арнольдов', 745452)]

@pytest.mark.parametrize('a, expected', generate_get_blacklist())
def test_get_blacklist(a, expected):
    assert get_blacklist(a) == expected


def generate_delete_favourite():
    yield 959555, 547465, 'Профиль удалён из списка избранного'

@pytest.mark.parametrize('a, b, expected', generate_delete_favourite())
def test_delete_favourite(a, b, expected):
    assert delete_favourite(a,b) == expected


def generate_delete_blacklist():
    yield 745452, 745455, 'Профиль удалён из чёрного списка'

@pytest.mark.parametrize('a, b, expected', generate_delete_blacklist())
def test_delete_blacklist(a, b, expected):
    assert delete_blacklist(a,b) == expected
