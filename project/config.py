from sqlalchemy.engine.url import URL
import os

TOKEN_GROUP = os.environ.get("TOKEN_GROUP", "YOUR_TOKEN_HERE")  # Получение из переменной окружения

GROUP_ID = 2  # id сообщества
APPLICATION_ID = 5  # id приложения авторизации

DB_NAME = os.environ.get("DB_NAME", "vkinder")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", " ")  # Получение из переменной окружения
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")

DNS = URL.create(
    drivername="postgresql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)
