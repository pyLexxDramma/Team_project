import vk_api
import json
import logging
import psycopg2
from psycopg2 import Error
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_NAME = "vkinder"
DB_USER = "postgres"
DB_PASSWORD = "ваш_пароль"
DB_HOST = "localhost"
DB_PORT = "5432"

def connect_db():
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        return conn
    except Error as e:
        logging.error(f"Ошибка подключения к базе данных: {e}")
        return None

def create_token_table(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                user_id INTEGER PRIMARY KEY,
                access_token TEXT,
                expires_in INTEGER,
                token_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
        """)
        conn.commit()
    except Error as e:
        logging.error(f"Ошибка при создании таблицы токенов: {e}")
        conn.rollback()

def save_token(conn, user_id, access_token, expires_in):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tokens (user_id, access_token, expires_in)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET access_token = EXCLUDED.access_token, expires_in = EXCLUDED.expires_in;
        """, (user_id, access_token, expires_in))
        conn.commit()
    except Error as e:
        logging.error(f"Ошибка при сохранении токена: {e}")
        conn.rollback()

def get_vk_token(app_id):
    # Использовать Selenium для авторизации и получения токена
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    driver.get(f'https://oauth.vk.com/authorize?client_id={app_id}&display=popup&redirect_uri=https://oauth.vk.com/blank.html&scope=friends&response_type=token&v=5.131')

    # Здесь добавить код для авторизации (логин/пароль или QR-код)
    # После успешной авторизации получить access_token и expires_in из URL
    # Пример: access_token и expires_in = driver.current_url.split('access_token=')[1].split('&')[0], driver.current_url.split('expires_in=')[1].split('&')[0]

    driver.quit()
    return access_token, expires_in

def check_token(conn, user_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT access_token, expires_in FROM tokens WHERE user_id = %s", (user_id,))
        token_data = cursor.fetchone()
        if token_data:
            access_token, expires_in = token_data
            # Проверка, не истек ли токен
            if expires_in > 0:
                return access_token
            else:
                logging.info("Токен истек, требуется новая авторизация.")
        return None
    except Error as e:
        logging.error(f"Ошибка при проверке токена: {e}")
        return None

def main():
    conn = connect_db()
    if not conn:
        return

    create_token_table(conn)

    user_id = 123456  # Заменить на реальный user_id
    app_id = 'ваш_app_id'

    access_token = check_token(conn, user_id)
    if not access_token:
        access_token, expires_in = get_vk_token(app_id)
        save_token(conn, user_id, access_token, expires_in)

    # Теперь можно использовать access_token для выполнения запросов к VK API

    conn.close()

if __name__ == '__main__':
    main()
