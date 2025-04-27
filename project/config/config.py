from sqlalchemy.engine.url import URL
import os

#  Важно: Укажите реальный токен группы!
TOKEN_GROUP = os.environ.get("TOKEN_GROUP", "YOUR_TOKEN_HERE")  # Получение из переменной окружения

GROUP_ID = 2  # id сообщества
APPLICATION_ID = 5  # id приложения авторизации

DB_NAME = os.environ.get("DB_NAME", "vkinder")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", " ")  # Получение из переменной окружения
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")

DSN = URL.create(
    drivername="postgresql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)

AGE_WEIGHT = 0.3
# вес (значимость) возраста при расчете общего "рейтинга" пользователя.
# Чем ближе возраст искомого пользователя к желаемому диапазону, тем выше его оценка.
INTERESTS_WEIGHT = 0.4
# вес совпадения интересов.
# Чем больше общих интересов (музыка, книги, группы и т. д.), тем выше оценка.
FRIENDS_WEIGHT = 0.3
# вес количества общих друзей.
# Чем больше общих друзей у пользователей, тем выше оценка.