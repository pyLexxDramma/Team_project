import datetime
import json

import psycopg2
import vk_api
from psycopg2 import Error
from vk_api import keyboard
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

TOKEN = "vk1.a.-sa9rqEDaz7HEzCF26rtdJO5153PDAg4WYWDW1uGLqlI3XDatRDvi58GOfD9Vh-LG_jIcUGjWvLO4JCJiKzvbt8II6nisDRbGjjATBl3lxeOZyQiDoaKGxGdFtb1BS1hP0R9TYtHkHOW3J7416RGz0QUHgZe-YIlgxojGWMH9SqEl1pe1bzhMRyIWqhQT5o7ceH-y3GOkrfXdGxnOCkkdw"
GROUP_ID = 230206374

DB_NAME = "vkinder"
DB_USER = "postgres"
DB_PASSWORD = "*****"
DB_HOST = "localhost"
DB_PORT = "5432"

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session, group_id=GROUP_ID)


user_states = {}

def connect_db():
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
        return conn
    except Error as e:
        print(f"Ошибка подключения к базе данных: {e}")
        return None

def create_db_tables(conn):
    try:
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
                target_user_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS favorites (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id),
                favorite_user_id INTEGER
            );
        """)
        conn.commit()
    except Error as e:
        print(f"Ошибка при создании таблиц: {e}")
        conn.rollback()

def get_vk_user_info(user_id):
    try:
        user_info = vk.users.get(user_ids=user_id, fields=['city', 'sex', 'bdate'])[0]
        return user_info
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка при получении информации о пользователе: {e}")
        return None

def calculate_age(birthdate_str):
    try:
        birthdate = datetime.datetime.strptime(birthdate_str, '%d.%m.%Y')
        today = datetime.datetime.now()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        return age
    except ValueError:
        return None

def save_user_to_db(conn, user_id, age, sex, city):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, age, sex, city)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
        """, (user_id, age, sex, city))
        conn.commit()
        return True
    except Error as e:
        print(f"Ошибка при сохранении информации о пользователе: {e}")
        conn.rollback()

def search_vk_users(user_info, offset=0, count=10):
    try:
        group_members = vk.groups.getMembers(group_id=GROUP_ID, offset=offset, count=count, fields=['city', 'sex', 'bdate'])
        return group_members['items']
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка при поиске пользователей в группе: {e}")
        return []

def filter_users(users, user_info):
    filtered_users = []
    for user in users:
        if 'city' in user and user['city']['title'].lower() == user_info['city'].lower():
            if 'sex' in user and user['sex'] == user_info['sex']:
                if 'bdate' in user:
                    age = calculate_age(user['bdate'])
                    if user_info['age_from'] <= age <= user_info['age_to']:
                        filtered_users.append(user)
    return filtered_users

def get_popular_vk_photos(user_id, count=3):
    try:
        photos = vk.photos.getAll(owner_id=user_id, extended=1, count=200)
        if 'items' not in photos:
            return []
        photos_with_likes = [(photo['id'], photo['likes']['count']) for photo in photos['items']]
        photos_with_likes.sort(key=lambda x: x[1], reverse=True)
        top_photos_ids = [f'photo{user_id}_{photo_id}' for photo_id, _ in photos_with_likes[:count]]
        return top_photos_ids
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка при получении фотографий: {e}")
        return []

def send_vk_user_info(user_id, target_user, keyboard=None):
    first_name = target_user['first_name']
    last_name = target_user['last_name']
    profile_url = f"https://vk.com/id{target_user['id']}"
    photos = get_popular_vk_photos(target_user['id'])
    attachments = ','.join(photos)
    message = f"{first_name} {last_name}\n{profile_url}"

    params = {
        'user_id': user_id,
        'message': message,
        'random_id': get_random_id(),
        'attachment': attachments
    }

    if keyboard:
        params['keyboard'] = json.dumps(keyboard)

    vk.messages.send(**params)

def add_user_to_favorites(conn, user_id, favorite_user_id):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO favorites (user_id, favorite_user_id)
            VALUES (%s, %s)
        """, (user_id, favorite_user_id))
        conn.commit()
        return True
    except Error as e:
        print(f"Ошибка при добавлении в избранное: {e}")
        conn.rollback()

def get_favorite_users(conn, user_id):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT favorite_user_id FROM favorites WHERE user_id = %s", (user_id,))
        favorite_users = [row[0] for row in cursor.fetchall()]
        return favorite_users
    except Error as e:
        print(f"Ошибка при получении списка избранных: {e}")
        return []

def display_favorite_users(user_id, favorites):
    if not favorites:
        send_message(user_id, "Ваш список избранных пуст.")
        return
    message = "Ваш список избранных:\n"
    for favorite_id in favorites:
        try:
            user = vk.users.get(user_ids=favorite_id)[0]
            message += f"- {user['first_name']} {user['last_name']} (https://vk.com/id{favorite_id})\n"
        except vk_api.exceptions.ApiError:
            message += f"- Пользователь с ID {favorite_id} не найден.\n"
    send_message(user_id, message)

def create_keyboard(buttons, one_time=True):
    keyboard = {
        "one_time": one_time,
        "buttons": buttons
    }
    return keyboard

def send_message(user_id, message, keyboard=None):
    params = {
        'user_id': user_id,
        'message': message,
        'random_id': get_random_id()
    }
    if keyboard:
        params['keyboard'] = json.dumps(keyboard)
    try:
      vk.messages.send(**params)
    except vk_api.exceptions.ApiError as e:
      print(f"Ошибка при отправке сообщения: {e}")

def ask_city(user_id):
    user_states[user_id] = {"state": "waiting_for_city", "data": {}}
    send_message(user_id, "Введите город для поиска:")

def ask_sex(user_id):
     user_states[user_id]["state"] = "waiting_for_sex"
     buttons = [
        [
            {
                "action": {
                    "type": "text",
                    "payload": json.dumps({"command": "set_sex", "sex": 1}),
                    "label": "Женский"
                },
                "color": "primary"
            }
        ],
        [
            {
                "action": {
                    "type": "text",
                    "payload": json.dumps({"command": "set_sex", "sex": 2}),
                    "label": "Мужской"
                },
                "color": "primary"
            }
        ],
        [
            {
                "action": {
                    "type": "text",
                    "payload": json.dumps({"command": "set_sex", "sex": 0}),
                    "label": "Не важно"
                },
                "color": "secondary"
            }
        ]
    ]
     keyboard = create_keyboard(buttons)
     send_message(user_id, "Выберите пол:", keyboard)

def ask_age(user_id):
    user_states[user_id]["state"] = "waiting_for_age"
    send_message(user_id, "Введите возраст для поиска (или диапазон через тире, например 20-30):")

def start_search(conn, user_id):
    if user_id not in user_states or "data" not in user_states[user_id]:
        send_message(user_id, "Произошла ошибка. Пожалуйста, начните поиск заново.")
        return

    data = user_states[user_id]["data"]
    age_str = data.get("age")
    age_from = None
    age_to = None

    if age_str:
        try:
            if "-" in age_str:
                age_from, age_to = map(int, age_str.split("-"))
            else:
                age_from = age_to = int(age_str)
        except ValueError:
            send_message(user_id, "Некорректный формат возраста.")
            return
    sex = data.get("sex")
    city = data.get("city")

    user_info = {
        "age_from": age_from,
        "age_to": age_to,
        "sex": sex,
        "city": city
    }
    if save_user_to_db(conn, user_id, age_from, sex, city):
        send_message(user_id, f"Начинаем поиск: Город: {city if city else 'Не указан'}, Пол: { 'женский' if sex == 1 else 'мужской' if sex == 2 else 'Не указан'}, Возраст: {age_str if age_str else 'Не указан'}")

        users = search_vk_users(user_info) # Получаем всех участников группы
        filtered_users = filter_users(users, user_info)  # Фильтруем по критериям

        del user_states[user_id]

        return filtered_users

    else:
         send_message(user_id, "Ошибка сохранения данных в базе.")
         return None

def handle_next_command(user_id, current_search_results, search_index):
    if user_id in current_search_results and current_search_results[user_id]:
        search_index[user_id] += 1
        if search_index[user_id] < len(current_search_results[user_id]):
            return current_search_results[user_id][search_index[user_id]]
        else:
            send_message(user_id, "Это был последний пользователь в результатах поиска.")
    else:
        send_message(user_id, "Сначала начните поиск, введя команду 'начать'.")
    return None

def handle_favorites_command(conn, user_id, current_search_results, search_index):
    if user_id in current_search_results and current_search_results[user_id]:
        target_user = current_search_results[user_id][search_index[user_id]]
        if add_user_to_favorites(conn, user_id, target_user['id']):
            send_message(user_id, "Пользователь добавлен в избранное!")
        else:
            send_message(user_id, "Этот пользователь уже в вашем списке избранных.")
    else:
        send_message(user_id, "Сначала начните поиск, введя команду 'начать'.")

def handle_show_favorites_command(conn, user_id):
    favorites = get_favorite_users(conn, user_id)
    display_favorite_users(user_id, favorites)

def process_command(message_text):
    try:
        data = json.loads(message_text)
        return data
    except (json.JSONDecodeError, TypeError):
        return {"command": message_text}

def main():
    conn = connect_db()
    if not conn:
        return

    create_db_tables(conn)

    current_search_results = {}
    search_index = {}

    try:
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
                user_id = event.user_id
                message_text = event.text.lower()
                data = process_command(message_text)
                command = data.get("command")

                print(f"main: user_id = {user_id}, message_text = {message_text}, command = {command}, user_states = {user_states.get(user_id)}")

                if not user_states.get(user_id) and command != 'начать':
                    start_button = [
                        [
                            {
                                "action": {
                                    "type": "text",
                                    "payload": json.dumps({"command": "начать"}),
                                    "label": "Начать"
                                },
                                "color": "primary"
                            }
                        ]
                    ]
                    send_message(user_id, "Добро пожаловать в VKinder! Нажмите кнопку 'Начать', чтобы запустить поиск.", create_keyboard(start_button))

                elif command == 'начать':
                     ask_city(user_id)

                elif user_id in user_states:
                    state = user_states[user_id]["state"]
                    user_data = user_states[user_id]["data"]

                    if state == "waiting_for_city":
                        user_data["city"] = message_text
                        ask_sex(user_id)

                    elif state == "waiting_for_sex":
                        if message_text == "женский":
                            user_data["sex"] = 1
                            ask_age(user_id)
                        elif message_text == "мужской":
                            user_data["sex"] = 2
                            ask_age(user_id)
                        elif message_text == "не важно":
                            user_data["sex"] = 0
                            ask_age(user_id)
                        else:
                            send_message(user_id, "Пожалуйста, выберите пол, используя кнопки.")

                    elif state == "waiting_for_age":
                        age_str = message_text
                        try:
                            if "-" in age_str:
                                age_from, age_to = map(int, age_str.split("-"))
                            else:
                                age_from = age_to = int(age_str)

                            user_data["age_from"] = age_from
                            user_data["age_to"] = age_to

                            current_search_results[user_id] = start_search(conn, user_id)
                            search_index[user_id] = 0 if current_search_results[user_id] else None

                            if current_search_results[user_id]:
                                keyboard = create_keyboard([[{
                                    "action": {
                                        "type": "text",
                                        "payload": json.dumps({"command": "дальше"}),
                                        "label": "Дальше"
                                    },
                                    "color": "primary"
                                },
                                {
                                    "action": {
                                        "type": "text",
                                        "payload": json.dumps({"command": "избранное"}),
                                        "label": "В избранное"
                                    },
                                    "color": "positive"
                                }],
                                [
                                    {
                                        "action": {
                                            "type": "text",
                                            "payload": json.dumps({"command": "список избранных"}),
                                            "label": "Список избранных"
                                        },
                                        "color": "secondary"
                                    }]])
                                send_vk_user_info(user_id, current_search_results[user_id][search_index[user_id]], keyboard)
                            else:
                                send_message(user_id, "Не найдено подходящих пользователей.")

                        except ValueError:
                            send_message(user_id, "Некорректный формат возраста.")


                elif command == 'дальше':
                    next_user = handle_next_command(user_id, current_search_results, search_index)
                    if next_user:
                        send_vk_user_info(user_id, next_user, keyboard)

                elif command == 'избранное':
                    handle_favorites_command(conn, user_id, current_search_results, search_index)

                elif command == 'список избранных':
                    handle_show_favorites_command(conn, user_id)

    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    main()