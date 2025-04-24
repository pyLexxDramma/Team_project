import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
import json
import logging
import psycopg2
from psycopg2 import Error
import datetime
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import asyncio
from functools import lru_cache

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Замените на токен пользователя, а не группы
TOKEN = 'str'
GROUP_ID = 000

access_token = 'str'

DB_NAME = "vkinder"
DB_USER = "postgres"
DB_PASSWORD = "str"
DB_HOST = "localhost"
DB_PORT = "5432"

AGE_WEIGHT = 0.3
INTERESTS_WEIGHT = 0.4
FRIENDS_WEIGHT = 0.3

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session, group_id=GROUP_ID)

vk_session_user = vk_api.VkApi(token=access_token)
vk_user = vk_session_user.get_api()
        
user_states = {}
current_search_results = {}
search_index = {}

def connect_db():
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        logging.info(f"Подключено к базе {DB_NAME} на {DB_HOST}")
        return conn
    except Error as e:
        logging.error(f"Ошибка подключения к базе данных: {e}")
        
        return None

def create_db_tables(conn):
    try:
        
        # cursor = conn.cursor()
        # # Удаляем старые таблицы 
        # cursor.execute("DROP TABLE IF EXISTS search_results, users, favorites, blacklist, user_interests")
        
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                age INTEGER,
                sex INTEGER,
                city TEXT
            );
            CREATE TABLE IF NOT EXISTS search_results (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id),
                target_user_id INTEGER,
                score REAL
            );
            CREATE TABLE IF NOT EXISTS favorites (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id),
                favorite_user_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS blacklist (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id),
                blacklisted_user_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS user_interests (
                user_id INTEGER PRIMARY KEY,
                interests TEXT
            );
        """)
        conn.commit()
        logging.info("Таблицы успешно созданы")
    except Error as e:
        logging.error(f"Ошибка при создании таблиц: {e}")
        conn.rollback()

def create_keyboard_start():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Начать", color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()

def create_keyboard_city():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Москва")
    keyboard.add_button("Санкт-Петербург")
    keyboard.add_line()
    keyboard.add_button("Ижевск")
    keyboard.add_button("Другой")
    return keyboard.get_keyboard()

def create_keyboard_sex():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Женский")
    keyboard.add_button("Мужской")
    keyboard.add_line()
    keyboard.add_button("Не важно")
    return keyboard.get_keyboard()

def create_keyboard_next_fav_black():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Дальше", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("Избранное", color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button("Черный список", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

def send_message(user_id, message, keyboard=None):
    try:
        vk.messages.send(
            user_id=user_id,
            message=message,
            random_id=get_random_id(),
            keyboard=keyboard
        )
    except vk_api.exceptions.ApiError as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")

def handle_blacklist_command(conn, user_id, blacklisted_user_id):
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO blacklist (user_id, blacklisted_user_id) VALUES (%s, %s)",
            (user_id, blacklisted_user_id)
        )
        conn.commit()
        send_message(user_id, "Пользователь добавлен в черный список.")
    except Error as e:
        logging.error(f"Ошибка при добавлении в черный список: {e}")
        conn.rollback()
        send_message(user_id, "Ошибка при добавлении в черный список.")

def is_user_blacklisted(conn, user_id, target_user_id):
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM blacklist WHERE user_id = %s AND blacklisted_user_id = %s",
            (user_id, target_user_id)
        )
        return cursor.fetchone() is not None
    except Error as e:
        logging.error(f"Ошибка при проверке черного списка: {e}")
        return False

def get_vk_user_info(user_id, fields=None):
    try:
        user_info = vk.users.get(user_ids=user_id, fields=fields)
        logging.debug(f"get_vk_user_info({user_id}, {fields}): {user_info}")
        if user_info and len(user_info) > 0:
            return user_info[0]
        else:
            return None
    except vk_api.exceptions.ApiError as e:
        logging.error(f"Ошибка при получении информации о пользователе: {e}")
        return None

def calculate_age(birthdate_str):
    try:
        birthdate = datetime.datetime.strptime(birthdate_str, '%d.%m.%Y')
        today = datetime.datetime.now()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        return age
    except (ValueError, TypeError):
        return None

@lru_cache(maxsize=128)
def get_user_interests(user_id):
    try:
        user_info = get_vk_user_info(user_id, fields=['interests', 'music', 'books', 'groups'])
        if not user_info:
            return ''

        interests = user_info.get('interests', '') + ' ' + user_info.get('music', '') + ' ' + user_info.get('books', '')
        group_ids = user_info.get('groups', '')
        
        if group_ids:
             groups = ','.join(group_ids.split(','))
        else:
            groups = ''

        interests += groups

        return interests
    except Exception as e:
        logging.error(f"Ошибка при получении интересов пользователя: {e}")
        return ''

def calculate_interests_similarity(user1_interests, user2_interests):
    try:
        if not user1_interests.strip() or not user2_interests.strip():
            return 0.0
        tfidf_vectorizer = TfidfVectorizer()
        tfidf_matrix = tfidf_vectorizer.fit_transform([user1_interests, user2_interests])
        similarity_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return similarity_score
    except Exception as e:
        logging.error(f"Ошибка при вычислении схожести интересов: {e}")
        return 0.0

async def fetch_friends(user_id):
    try:
        response = await asyncio.to_thread(vk_user.friends.get, user_id=user_id)
        return response['items']
    except vk_api.exceptions.ApiError as e:
        logging.error(f"Ошибка при получении друзей пользователя {user_id}: {e}")
        return []

async def get_common_friends_count(user_id, target_user_id):
    try:
        friends1 = await fetch_friends(user_id)
        friends2 = await fetch_friends(target_user_id)
        common_friends = set(friends1) & set(friends2)
        return len(common_friends)
    except Exception as e:
        logging.error(f"Ошибка при получении общих друзей: {e}")
        return 0

def get_city_id(city_name):
    """Получает ID города по названию"""
    try:
        response = vk_user.database.getCities(q=city_name, count=1)
        if response['items']:
            return response['items'][0]['id']
        return None
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка при получении ID города: {e}")
        return None

def search_vk_users(conn, user_info, current_user_id):
    try:
        
        city_id = get_city_id(user_info['city'])
        
        params = {
            'city': city_id,
            'age_from': user_info['age_from'],
            'age_to': user_info['age_to'],
            'sex': user_info['sex'],
            'count': 10,
            'fields': 'city, sex, bdate, interests, music, books, groups',
            'status': 6  # В активном поиске
        }
        response = vk_user.users.search(**params)
        users = response['items']
        logging.info(f"Найдено пользователей: {len(users)}")
        filtered_users = []
        for user_data in users:
            if is_user_blacklisted(conn, current_user_id, user_data['id']):
                continue

            age = calculate_age(user_data.get('bdate', ''))
            if age is None:
                logging.debug(f"Не удалось определить возраст пользователя {user_data['id']}")
                continue

            filtered_users.append(user_data)
        return filtered_users
    except vk_api.exceptions.ApiError as e:
        logging.error(f"Ошибка при поиске пользователей: {e}")
        return []

def evaluate_user(user_id, target_user, search_user_info, conn):
    try:
        target_age = calculate_age(target_user.get('bdate', ''))
        if target_age is None:
            return 0.0
        age_diff = abs(search_user_info['age_from'] - target_age) if target_age else 100
        age_score = 1 - (age_diff / 100)

        search_user_interests = get_user_interests(search_user_info['user_id'])
        target_user_interests = get_user_interests(target_user['id'])
        interests_similarity = calculate_interests_similarity(search_user_interests, target_user_interests)

        common_friends_count = asyncio.run(get_common_friends_count(search_user_info['user_id'], target_user['id']))

        friends_score = common_friends_count / 100 if common_friends_count <= 100 else 1
        final_score = (AGE_WEIGHT * age_score) + (INTERESTS_WEIGHT * interests_similarity) + (FRIENDS_WEIGHT * friends_score)

        return final_score
    except Exception as e:
        logging.error(f"Ошибка при оценке пользователя: {e}")
        return 0.0

def handle_next_command(conn, user_id):
    global search_index, current_search_results
    if user_id in current_search_results:
        search_index[user_id] = search_index.get(user_id, 0) + 1
        if search_index[user_id] < len(current_search_results[user_id]):
            target_user = current_search_results[user_id][search_index[user_id]]
            
            try:
                 cursor = conn.cursor()
                 cursor.execute("SELECT score FROM search_results WHERE user_id = %s AND target_user_id = %s", (user_id, target_user['id']))
                 (score,) = cursor.fetchone()
                 send_message(user_id, f"Следующий пользователь: {target_user.get('first_name', 'Имя')} {target_user.get('last_name', 'Фамилия')}, Score: {score:.2f}", keyboard=create_keyboard_next_fav_black())
            except Exception as e:
                 logging.error(f"Ошибка при получении оценки пользователя из БД: {e}")

        else:
            send_message(user_id, "Это был последний пользователь в результатах поиска.")
            del current_search_results[user_id]
            del search_index[user_id]
    else:
        send_message(user_id, "Сначала начните поиск, введя команду 'начать'.")

def handle_favorites_command(conn, user_id):
    if user_id in current_search_results and search_index.get(user_id) is not None:
        target_user = current_search_results[user_id][search_index[user_id]]
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO favorites (user_id, favorite_user_id) VALUES (%s, %s)", (user_id, target_user['id']))
            conn.commit()
            send_message(user_id, f"Пользователь {target_user.get('first_name', 'Имя')} {target_user.get('last_name', 'Фамилия')} добавлен в избранное.")
        except Error as e:
            logging.error(f"Ошибка при добавлении в избранное: {e}")
            conn.rollback()
            send_message(user_id, "Ошибка при добавлении в избранное.")
    else:
        send_message(user_id, "Сначала начните поиск, введя команду 'начать'.")

def handle_show_favorites_command(conn, user_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT favorite_user_id FROM favorites WHERE user_id = %s", (user_id,))
        favorite_users = [row[0] for row in cursor.fetchall()]
        if not favorite_users:
            send_message(user_id, "Ваш список избранных пуст.")
            return

        message = "Ваш список избранных:\n"
        for favorite_id in favorite_users:
            user = get_vk_user_info(favorite_id)
            if user:
                message += f"- {user.get('first_name', 'Имя')} {user.get('last_name', 'Фамилия')} (https://vk.com/id{favorite_id})\n"
            else:
                message += f"- Пользователь с ID {favorite_id} не найден.\n"
        send_message(user_id, message)
    except Error as e:
        logging.error(f"Ошибка при получении списка избранных: {e}")
        send_message(user_id, "Ошибка при получении списка избранных.")

def handle_blacklist_command(conn, user_id):
    if user_id in current_search_results and search_index.get(user_id) is not None:
        target_user = current_search_results[user_id][search_index[user_id]]
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO blacklist (user_id, blacklisted_user_id) VALUES (%s, %s)", (user_id, target_user['id']))
            conn.commit()
            send_message(user_id, f"Пользователь {target_user.get('first_name', 'Имя')} {target_user.get('last_name', 'Фамилия')} добавлен в черный список.")
        except Error as e:
            logging.error(f"Ошибка при добавлении в черный список: {e}")
            conn.rollback()
            send_message(user_id, "Ошибка при добавлении в черный список.")
    else:
        send_message(user_id, "Сначала начните поиск, введя команду 'начать'.")

def main():
    
    conn = connect_db()
    if not conn:
        return
    create_db_tables(conn)
    global current_search_results, search_index
    try:
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
                user_id = event.user_id
                message_text = event.text.lower()

                if not user_states.get(user_id) and message_text != 'начать':
                    keyboard = create_keyboard_start()
                    send_message(user_id, "Добро пожаловать! Нажмите 'Начать'.", keyboard=keyboard)
                elif message_text == 'начать':
                    user_states[user_id] = {"state": "waiting_for_city", "data": {}}
                    keyboard = create_keyboard_city()
                    send_message(user_id, "Выберите город:", keyboard=keyboard)
                elif user_id in user_states:
                    state = user_states[user_id]["state"]
                    user_data = user_states[user_id]["data"]
                    if state == "waiting_for_city":
                        user_data["city"] = message_text
                        user_states[user_id]["state"] = "waiting_for_sex"
                        keyboard = create_keyboard_sex()
                        send_message(user_id, "Выберите пол:", keyboard=keyboard)
                    elif state == "waiting_for_sex":
                        if message_text == "женский":
                            user_data["sex"] = 1
                        elif message_text == "мужской":
                            user_data["sex"] = 2
                        else:
                            user_data["sex"] = 0
                        user_states[user_id]["state"] = "waiting_for_age"
                        send_message(user_id, "Введите возраст (или диапазон через тире, например 20-30):")
                    elif state == "waiting_for_age":
                        age_str = message_text
                        try:
                            if "-" in age_str:
                                age_from, age_to = map(int, age_str.split("-"))
                            else:
                                age_from = age_to = int(age_str)

                            user_info = {"user_id": user_id, "age_from": age_from, "age_to": age_to, "sex": user_data["sex"], "city": user_data["city"]}
                            search_users = search_vk_users(conn, user_info, user_id)
                            scored_users = []
                            for target_user in search_users:
                                score = evaluate_user(user_id, target_user, user_info, conn)
                                
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute("INSERT INTO search_results (user_id, target_user_id, score) VALUES (%s, %s, %s)", (user_id, target_user['id'], score))
                                    conn.commit()
                                except Exception as e:
                                    logging.error(f"Ошибка при записи оценки пользователя в БД: {e}")

                                scored_users.append((target_user, score))

                            scored_users.sort(key=lambda x: x[1], reverse=True)

                            current_search_results[user_id] = [user for user, score in scored_users]
                            search_index[user_id] = 0

                            if current_search_results[user_id]:
                                target_user = current_search_results[user_id][0]
                                try:
                                     cursor = conn.cursor()
                                     cursor.execute("SELECT score FROM search_results WHERE user_id = %s AND target_user_id = %s", (user_id, target_user['id']))
                                     (score,) = cursor.fetchone()
                                     send_message(user_id, f"Найден первый пользователь: {target_user.get('first_name', 'Имя')} {target_user.get('last_name', 'Фамилия')}, Score: {score:.2f}", keyboard=create_keyboard_next_fav_black())
                                except Exception as e:
                                     logging.error(f"Ошибка при получении оценки пользователя из БД: {e}")
                            else:
                                send_message(user_id, "Пользователи не найдены.")
                        except ValueError:
                            send_message(user_id, "Некорректный формат возраста.")
                        except Exception as e:
                            logging.exception("Ошибка при обработке возраста:")

                    elif message_text == 'дальше':
                        handle_next_command(conn, user_id)
                    elif message_text == 'избранное':
                        handle_favorites_command(conn, user_id)
                    elif message_text == 'черный список':
                        handle_blacklist_command(conn, user_id)
                    elif message_text == 'список избранных':
                        handle_show_favorites_command(conn, user_id)

    except Exception as e:
        logging.exception("Ошибка в основном цикле:")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print('Бот запущен !')
    main()

