import logging
import psycopg2
from psycopg2 import Error
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from urllib.parse import urlparse


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# def connect_db():
#     try:
#         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
#         return conn
#     except Error as e:
#         logging.error(f"Ошибка подключения к базе данных: {e}")
#         return None

# def create_token_table(conn):
#     try:
#         cursor = conn.cursor()
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS tokens (
#                 user_id INTEGER PRIMARY KEY,
#                 access_token TEXT,
#                 expires_in INTEGER,
#                 token_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                 FOREIGN KEY (user_id) REFERENCES users(user_id)
#             );
#         """)
#         conn.commit()
#     except Error as e:
#         logging.error(f"Ошибка при создании таблицы токенов: {e}")
#         conn.rollback()

# def save_token(conn, user_id, access_token, expires_in):
#     try:
#         cursor = conn.cursor()
#         cursor.execute("""
#             INSERT INTO tokens (user_id, access_token, expires_in)
#             VALUES (%s, %s, %s)
#             ON CONFLICT (user_id) DO UPDATE SET access_token = EXCLUDED.access_token, expires_in = EXCLUDED.expires_in;
#         """, (user_id, access_token, expires_in))
#         conn.commit()
#     except Error as e:
#         logging.error(f"Ошибка при сохранении токена: {e}")
#         conn.rollback()

def get_vk_token(APPLICATION_ID):
    """
    Получает access_token для VK API через OAuth 2.0 (авторизация через браузер).
    Args:
        APPLICATION_ID (int): ID приложения VK.
    Returns:
        str: access_token или None в случае ошибки.
    """
    driver = webdriver.Chrome()
    auth_url = f"https://oauth.vk.com/authorize?client_id={APPLICATION_ID}&display=page&redirect_uri=https://example.com/callback&scope=friends&response_type=token&v=5.131&state=123456"
    try:
        driver.get(auth_url)
        WebDriverWait(driver, 60).until(
            lambda d: "example.com/callback" in d.current_url)
        redirect_url = driver.current_url
        parsed_url = urlparse(redirect_url)
        fragment = parsed_url.fragment
        params = dict(param.split('=') for param in fragment.split('&'))
        
        if "access_token" in params:
            access_token = params["access_token"]
            return access_token
        else:
            print("Не удалось найти access_token в URL.")
            return None
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return None
    finally:
        driver.quit()

# def check_token(conn, user_id):
#     try:
#         cursor = conn.cursor()
#         cursor.execute("SELECT access_token, expires_in FROM tokens WHERE user_id = %s", (user_id,))
#         token_data = cursor.fetchone()
#         if token_data:
#             access_token, expires_in = token_data
#             # Проверка, не истек ли токен
#             if expires_in > 0:
#                 return access_token
#             else:
#                 logging.info("Токен истек, требуется новая авторизация.")
#         return None
#     except Error as e:
#         logging.error(f"Ошибка при проверке токена: {e}")
#         return None
