import logging
from selenium import webdriver
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from urllib.parse import urlparse
from config import *
from create_db import *
from datetime import datetime, timedelta, timezone


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

def check_token(user_id):
    session = init_db()
    try:
        # 1. Проверяем последний токен пользователя
        token_record = session.query(AccessTokenUser)\
            .filter_by(user_id=user_id)\
            .order_by(AccessTokenUser.data_time.desc())\
            .first()
        
        # 2. Если токен есть и он свежий (меньше 23 часов) - возвращаем его
        if token_record and (datetime.now(timezone.utc) - token_record.data_time < timedelta(hours=23)):
            return token_record.access_token
        
        # 3. Получаем новый токен через VK OAuth
        new_token = get_vk_token(APPLICATION_ID)
        if not new_token:
            logging.error("Не удалось получить новый токен")
            return None
            
        # 4. Сохраняем в AccessTokenUser
        if token_record:
            # Обновляем существующую запись
            token_record.access_token = new_token
            token_record.data_time = datetime.now(timezone.utc)
        else:
            # Создаем новую запись
            new_token_record = AccessTokenUser(
                user_id=user_id,
                access_token=new_token,
                data_time=datetime.now(timezone.utc)
            )
            session.add(new_token_record)
        
        session.commit()
        return new_token
        
    except Exception as e:
        logging.error(f"Ошибка при проверке токена: {e}")
        session.rollback()
        return None        
        