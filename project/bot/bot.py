from pprint import pprint
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from sklearn.metrics.pairwise import cosine_similarity
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from functools import lru_cache
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent)) 
from create_keyboard.create_keyboard import *
from psycopg2 import Error
from BD_tokens.BD_tokens import *
from config.config import *
from VKinder_db.create_db import* 
from VKinder_db.models import* 
import datetime
import logging
import vk_api

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Инициализация VK API
vk_session = vk_api.VkApi(token=TOKEN_GROUP) 
vk = vk_session.get_api()
# longpoll = VkLongPoll(vk_session, group_id=GROUP_ID)
longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID)

# Глобальные переменные для хранения состояния
user_states = {}            # Текущее состояние пользователей (FSM)
current_search_results = {} # Результаты поиска для каждого пользователя
search_index = {}           # Индекс текущего просматриваемого результата


def send_message(user_id, message, keyboard=None):
    """Отправляет сообщение пользователю в VK."""
    try:
        vk.messages.send(
            user_id=user_id,
            message=message,
            random_id=get_random_id(),
            keyboard=keyboard
        )
    except vk_api.exceptions.ApiError as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")


def get_vk_user_info(user_id, fields=None):
    """Получает информацию о пользователе VK."""
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
    """Вычисляет возраст по дате рождения."""
    try:
        birthdate = datetime.datetime.strptime(birthdate_str, '%d.%m.%Y')
        today = datetime.datetime.now()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        return age
    except (ValueError, TypeError):
        return None


def get_city_id(city_name):
    """Получает ID города по названию."""
    try:
        response = vk_user.database.getCities(q=city_name, count=1)
        if response['items']:
            return response['items'][0]['id']
        return None
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка при получении ID города: {e}")
        return None


def search_vk_users(user_info):
    """Ищет пользователей VK по заданным критериям."""
    try:
        global vk_user, token
        token = check_token(user_info['user_id'])

        vk_session_user = vk_api.VkApi(token=token)
        vk_user = vk_session_user.get_api()

        city_id = get_city_id(user_info['city'])

        params = {
            'city': city_id,
            'age_from': user_info['age_from'],
            'age_to': user_info['age_to'],
            'sex': user_info['sex'],
            'count': 10,
            'fields': 'city, sex, bdate, interests, music, books, groups, crop_photo',
            'status': 6  # В активном поиске
        }
        response = vk_user.users.search(**params)
        users = response['items']
        logging.info(f"Найдено пользователей: {len(users)}")

        filtered_users = []
        for user_data in users:
            if get_blacklist(user_data['id']):
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

def handle_favorites_command(conn, user_id):
    """Добавляет текущего пользователя в избранное."""
    if user_id in current_search_results and search_index.get(user_id) is not None:
        target_user = current_search_results[user_id][search_index[user_id]]
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO favorites (user_id, favorite_user_id) VALUES (%s, %s)",
                (user_id, target_user['id'])
            )
            conn.commit()
            send_message(user_id, f"Пользователь {target_user.get('first_name', 'Имя')} {target_user.get('last_name', 'Фамилия')} добавлен в избранное.")
        except Error as e:
            logging.error(f"Ошибка при добавлении в избранное: {e}")
            conn.rollback()
            send_message(user_id, "Ошибка при добавлении в избранное.")
    else:
        send_message(user_id, "Сначала начните поиск, введя команду 'начать'.")


def handle_show_favorites_command(conn, user_id):
    """Показывает список избранных пользователей."""
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
    """Добавляет текущего пользователя в черный список."""
    if user_id in current_search_results and search_index.get(user_id) is not None:
        target_user = current_search_results[user_id][search_index[user_id]]
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO blacklist (user_id, blacklisted_user_id) VALUES (%s, %s)",
                (user_id, target_user['id'])
            )
            conn.commit()
            send_message(user_id, f"Пользователь {target_user.get('first_name', 'Имя')} {target_user.get('last_name', 'Фамилия')} добавлен в черный список.")
        except Error as e:
            logging.error(f"Ошибка при добавлении в черный список: {e}")
            conn.rollback()
            send_message(user_id, "Ошибка при добавлении в черный список.")
    else:
        send_message(user_id, "Сначала начните поиск, введя команду 'начать'.")


def add_user_db(vk_user_info):
    """Обрабатывает и сохраняет данные пользователя VK в базу данных."""
    try:
        vk_id = int(vk_user_info['id'])
        first_name = str(vk_user_info.get('first_name', ''))[:20]
        if not first_name:
            first_name = 'Неизвестно'

        city = 'Не указан'
        if 'city' in vk_user_info:
            if isinstance(vk_user_info['city'], dict):
                city = vk_user_info['city'].get('title', 'Не указан')
            else:
                city = str(vk_user_info['city'])

        age = 0  # Значение по умолчанию
        if 'bdate' in vk_user_info and vk_user_info['bdate']:
            bdate_parts = vk_user_info['bdate'].split('.')
            if len(bdate_parts) == 3:  # Полная дата (день.месяц.год)
                try:
                    age = calculate_age(vk_user_info['bdate']) or 0
                except Exception as e:
                    logging.warning(f"Ошибка вычисления возраста: {e}")
            else:
                logging.info(f"Пользователь {vk_id}: указана неполная дата рождения")

        sex = str(vk_user_info.get('sex', 0))
        if sex == '1':
            sex = 'женщина'
        elif sex == '2':
            sex = 'мужчина'
        else:
            sex = 'не известный'
        sex = sex[:10]

        result = add_user(
            vk_id=vk_id,
            first_name=first_name,
            age=age,
            sex=sex,
            city=city
        )
        logging.info(result)
    except Exception as e:
        logging.info(f'Ошибка в добавление данных пользователя{e}')



def send_user_profile(user_id, list_users, current_index=0):
    """Отправляет профиль пользователя с фотографиями"""
    try:
        if current_index >= len(list_users):
            send_message(user_id, "Анкеты закончились!")
            return
        
        user = list_users[current_index]
        
        current_search_results[user_id] = list_users
        search_index[user_id] = current_index
        
        message = f"Анкета {current_index + 1}/{len(list_users)}\n"
        message += f"{user['first_name']} {user['last_name']}\n"
        
        if user.get('bdate'):
            age = calculate_age(user['bdate'])
            if age:
                message += f"Возраст: {age} лет\n"
                
        if user.get('city'):
            message += f"Город: {user['city']['title']}\n"

        # Получаем фотографии
        attachments = []
        if user.get('crop_photo') and user['crop_photo'].get('photo'):
            photo = user['crop_photo']['photo']
            # Формируем attachment для фото
            attachment_str = f"photo{photo['owner_id']}_{photo['id']}_{token}"
            attachments.append(attachment_str)
        
        keyboard = {
            "inline": True,
            "buttons": [
                [
                    {
                        "action": {
                            "type": "text",
                            "label": "❤️ В избранное",
                            "payload": json.dumps({
                                "user_id": user['id'],
                                "action": "add_favorite",
                                "current_index": current_index
                            })
                        },
                        "color": "positive"
                    },
                    {
                        "action": {
                            "type": "text",
                            "label": "🚫 В ЧС",
                            "payload": json.dumps({
                                "user_id": user['id'],
                                "action": "add_blacklist",
                                "current_index": current_index
                            })
                        },
                        "color": "negative"
                    }
                ],
                [
                    {
                        "action": {
                            "type": "open_link",
                            "label": "🔗 Профиль",
                            "link": f"https://vk.com/id{user['id']}"
                        }
                    }
                ],
                [
                    {
                        "action": {
                            "type": "text",
                            "label": "➡️ Далее",
                            "payload": json.dumps({
                                "action": "next_profile",
                                "current_index": current_index
                            })
                        },
                        "color": "primary"
                    }
                ]
            ]
        }
        
        # Параметры для отправки
        params = {
            'user_id': user_id,
            'message': message,
            'random_id': get_random_id(),
            'keyboard': json.dumps(keyboard)
        }
        
        if attachments:
            params['attachment'] = ",".join(attachments)
        
        vk.messages.send(**params)
        
        
    except vk_api.exceptions.ApiError as e:
        logging.error(f"Ошибка отправки профиля: {e}")


# def main():
#     """Основная функция бота: инициализирует БД и запускает бесконечный цикл."""
#     conn = connect_db()
#     if not conn:
#         raise RuntimeError("Не удалось подключиться к базе данных")
#     create_tables(conn)
    
#     global current_search_results, search_index
    
#     try:
#         for event in longpoll.listen():
#             if event.type == VkBotEventType.MESSAGE_NEW and event.from_user and event.message.get('text'):
#                 user_id = event.message['from_id']
#                 message_text = event.message['text'].lower()
#             # if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
#                 # user_id = event.user_id
#                 # message_text = event.text.lower()
                
                
#                 vk_user_info = get_vk_user_info(user_id, fields=['first_name', 'city', 'bdate', 'sex'])
                
#                 if vk_user_info:
#                     add_user_db(vk_user_info)

#                 if not user_states.get(user_id) and message_text != 'начать':
#                     keyboard = create_keyboard_start()
#                     send_message(user_id, "Добро пожаловать! Нажмите 'Начать'.", keyboard=keyboard)

#                 elif message_text == 'начать':
#                     user_states[user_id] = {"state": "waiting_for_city", "data": {}}
#                     keyboard = create_keyboard_city()
#                     send_message(user_id, "Выберите город:", keyboard=keyboard)

#                 elif user_id in user_states:
#                     state = user_states[user_id]["state"]
#                     user_data = user_states[user_id]["data"]

#                     if state == "waiting_for_city":
#                         user_data["city"] = message_text
#                         user_states[user_id]["state"] = "waiting_for_sex"
#                         keyboard = create_keyboard_sex()
#                         send_message(user_id, "Выберите пол:", keyboard=keyboard)

#                     elif state == "waiting_for_sex":
#                         if message_text == "женский":
#                             user_data["sex"] = 1
#                         elif message_text == "мужской":
#                             user_data["sex"] = 2
#                         else:
#                             user_data["sex"] = 0
#                         user_states[user_id]["state"] = "waiting_for_age"
#                         send_message(user_id, "Введите возраст (или диапазон через тире, например 20-30):")

#                     elif state == "waiting_for_age":
#                         age_str = message_text
#                         try:
#                             if "-" in age_str:
#                                 age_from, age_to = map(int, age_str.split("-"))
#                             else:
#                                 age_from = age_to = int(age_str)

#                             user_info = {"user_id": user_id, "age_from": age_from, "age_to": age_to,
#                                          "sex": user_data["sex"], "city": user_data["city"]}
#                             list_users = search_vk_users(user_info)
                            
#                             current_search_results[user_id] = list_users
#                             search_index[user_id] = 0
                           
#                             send_user_profile(user_id, list_users)
#                         except vk_api.exceptions.ApiError as e:
#                             print(f'ошибка  {e}')
            
#             # Обработка нажатий inline-кнопок
#             elif event.type == VkBotEventType.MESSAGE_EVENT:
#                 payload = json.loads(event.obj['payload'])
#                 user_id = event.obj['user_id']
                
#                 if payload['action'] == 'add_favorite':
#                     if user_id in current_search_results:
#                         current_index = payload.get('current_index', 0)
#                         target_user = current_search_results[user_id][current_index]
#                         try:
#                             cursor = conn.cursor()
#                             cursor.execute(
#                                 "INSERT INTO favorites (user_id, favorite_user_id) VALUES (%s, %s)",
#                                 (user_id, target_user['id'])
#                             )
#                             conn.commit()
#                             send_message(user_id, f"Добавлено в избранное: {target_user['first_name']} {target_user['last_name']}")
#                         except Error as e:
#                             logging.error(f"Ошибка при добавлении в избранное: {e}")
#                             conn.rollback()
                
#                 elif payload['action'] == 'add_blacklist':
#                     if user_id in current_search_results:
#                         current_index = payload.get('current_index', 0)
#                         target_user = current_search_results[user_id][current_index]
#                         try:
#                             cursor = conn.cursor()
#                             cursor.execute(
#                                 "INSERT INTO blacklist (user_id, blacklisted_user_id) VALUES (%s, %s)",
#                                 (user_id, target_user['id'])
#                             )
#                             conn.commit()
#                             send_message(user_id, f"Добавлено в ЧС: {target_user['first_name']} {target_user['last_name']}")
#                         except Error as e:
#                             logging.error(f"Ошибка при добавлении в ЧС: {e}")
#                             conn.rollback()
                
#                 elif payload['action'] == 'next_profile':
#                     current_index = payload.get('current_index', 0) + 1
#                     if user_id in current_search_results and current_index < len(current_search_results[user_id]):
#                         send_user_profile(user_id, current_search_results[user_id], current_index)
#                     else:
#                         send_message(user_id, "Анкеты закончились, начните поиск заново!")
        
        
#     except vk_api.exceptions.ApiError as e:
#         logging.exception("Ошибка в основном цикле:")
#     # finally:
#     #     if conn:
#     #         conn.close()

def main():
    """Основная функция бота: инициализирует БД и запускает бесконечный цикл."""
    conn = connect_db()
    if not conn:
        raise RuntimeError("Не удалось подключиться к базе данных")
    create_tables(conn)
    global current_search_results, search_index
    try:
        for event in longpoll.listen():
            # Обработка нажатий inline-кнопок
            if event.type == VkBotEventType.MESSAGE_EVENT:
                try:
                    payload = json.loads(event.obj['payload'])
                    user_id = event.obj['user_id']
                    
                    if payload['action'] == 'add_favorite':
                        if user_id in current_search_results:
                            current_index = payload.get('current_index', 0)
                            target_user = current_search_results[user_id][current_index]
                            try:
                                pass
                            except Error as e:
                                logging.error(f"Ошибка при добавлении в избранное: {e}")
                                conn.rollback()
                    
                    elif payload['action'] == 'add_blacklist':
                        if user_id in current_search_results:
                            current_index = payload.get('current_index', 0)
                            target_user = current_search_results[user_id][current_index]
                            try:
                                pass
                            except Error as e:
                                logging.error(f"Ошибка при добавлении в ЧС: {e}")
                                conn.rollback()
                    
                    elif payload['action'] == 'next_profile':
                        current_index = payload.get('current_index', 0) + 1
                        if user_id in current_search_results and current_index < len(current_search_results[user_id]):
                            send_user_profile(user_id, current_search_results[user_id], current_index)
                        else:
                            send_message(user_id, "Анкеты закончились! Начните новый поиск.")
                
                except Exception as e:
                    logging.error(f"Ошибка обработки callback: {e}")
                continue  # Пропускаем обработку как обычное сообщение
            
            # Обработка обычных сообщений (только если это не callback)
            if event.type == VkBotEventType.MESSAGE_NEW and event.from_user and event.message.get('text'):
                user_id = event.message['from_id']
                message_text = event.message['text'].lower()
                
                # Проверяем, не является ли сообщение результатом нажатия кнопки
                if message_text in ['❤️ в избранное', '🚫 в чс', '➡️ далее', '🔗 профиль']:
                    continue
                
                # Получаем информацию о пользователе
                vk_user_info = get_vk_user_info(user_id, fields=['first_name', 'city', 'bdate', 'sex'])
                if vk_user_info:
                    add_user_db(vk_user_info)

                # Обработка команд
                if not user_states.get(user_id):
                    if message_text == 'начать':
                        user_states[user_id] = {"state": "waiting_for_city", "data": {}}
                        keyboard = create_keyboard_city()
                        send_message(user_id, "Введите название города для поиска:", keyboard=keyboard)
                    else:
                        keyboard = create_keyboard_start()
                        send_message(user_id, "Добро пожаловать! Нажмите 'Начать'.", keyboard=keyboard)
                    continue
                
                # Обработка состояний FSM
                state = user_states[user_id]["state"]
                user_data = user_states[user_id]["data"]

                if state == "waiting_for_city":
                    user_data["city"] = message_text
                    user_states[user_id]["state"] = "waiting_for_sex"
                    keyboard = create_keyboard_sex()
                    send_message(user_id, "Выберите пол для поиска:", keyboard=keyboard)

                elif state == "waiting_for_sex":
                    if message_text == "женский":
                        user_data["sex"] = 1
                    elif message_text == "мужской":
                        user_data["sex"] = 2
                    else:
                        user_data["sex"] = 0
                    user_states[user_id]["state"] = "waiting_for_age"
                    send_message(user_id, "Введите возраст или диапазон (например: 25-30):")

                elif state == "waiting_for_age":
                    try:
                        if "-" in message_text:
                            age_from, age_to = map(int, message_text.split("-"))
                        else:
                            age_from = age_to = int(message_text)

                        user_info = {
                            "user_id": user_id,
                            "age_from": age_from,
                            "age_to": age_to,
                            "sex": user_data["sex"],
                            "city": user_data["city"]
                        }
                        
                        list_users = search_vk_users(user_info)
                        if list_users:
                            current_search_results[user_id] = list_users
                            search_index[user_id] = 0
                            send_user_profile(user_id, list_users)
                        else:
                            send_message(user_id, "По вашему запросу ничего не найдено. Попробуйте другие критерии.")
                            user_states[user_id] = None  # Сбрасываем состояние
                    except ValueError:
                        send_message(user_id, "Пожалуйста, введите возраст числом или диапазон (например 25-30)")
        
    except Exception as e:
        logging.exception("Ошибка в основном цикле:")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print('Бот запущен !')
    main()


# Возможные проблемы:
# 1 у пользователя может быть скрыты дата рождения, или может быть видно только день и месяц, и мы не сможем его добавить в базу данных, если  мы уберем 
# огранечение в таблице user что у нас возраст может быть нулевым значением, либо если мы не можем вычеслит возраст то можем по дефолту ставить просто ноль



# def send_carousel_to_user(user_id, users_list, vk) :
#     """Отправляет карусель с пользователями указанному user_id"""
#     try:
#         # Создаем карусель
#         carousel_template = create_carousel_from_users(users_list, vk)
        
#         if carousel_template['elements']:
#             vk.messages.send(
#             user_id=user_id,
#             message="Подходящие анкеты:",
#             template=json.dumps(carousel_template),
#             random_id=random.randint(1, 10000)
#     )
         
#         return True
#     except vk_api.exceptions.ApiError as e:
#         print(f"Ошибка при отправке карусели: {e}")
#         return False




# def handle_next_command(conn, user_id):
#     """Обрабатывает команду "Дальше" (показывает следующего пользователя)."""
#     global search_index, current_search_results
#     if user_id in current_search_results:
#         search_index[user_id] = search_index.get(user_id, 0) + 1
#         if search_index[user_id] < len(current_search_results[user_id]):
#             target_user = current_search_results[user_id][search_index[user_id]]

#             score = get_user_score(conn, user_id, target_user['id'])
#             if score is not None:
#                 send_message(user_id, f"Следующий пользователь: {target_user.get('first_name', 'Имя')} {target_user.get('last_name', 'Фамилия')}, Score: {score:.2f}", keyboard=create_keyboard_next_fav_black())
#             else:
#                 send_message(user_id, "Ошибка при получении оценки пользователя.")  # Сообщение об ошибке

#         else:
#             send_message(user_id, "Это был последний пользователь в результатах поиска.")
#             del current_search_results[user_id]
#             del search_index[user_id]
#     else:
#         send_message(user_id, "Сначала начните поиск, введя команду 'начать'.")




# def evaluate_user(user_id, target_user, search_user_info, conn):
#     """Оценивает пользователя по возрасту, интересам и общим друзьям."""
#     try:
#         target_age = calculate_age(target_user.get('bdate', ''))
#         if target_age is None:
#             return 0.0
#         age_diff = abs(search_user_info['age_from'] - target_age) if target_age else 100
#         age_score = 1 - (age_diff / 100)

#         search_user_interests = get_user_interests(search_user_info['user_id'])
#         target_user_interests = get_user_interests(target_user['id'])
#         interests_similarity = calculate_interests_similarity(search_user_interests, target_user_interests)

#         common_friends_count = asyncio.run(get_common_friends_count(search_user_info['user_id'], target_user['id']))

#         friends_score = common_friends_count / 100 if common_friends_count <= 100 else 1
#         final_score = (AGE_WEIGHT * age_score) + (INTERESTS_WEIGHT * interests_similarity) + (FRIENDS_WEIGHT * friends_score)

#         return final_score
#     except Exception as e:
#         logging.error(f"Ошибка при оценке пользователя: {e}")
#         return 0.0


# def get_user_score(conn, user_id, target_user_id):
#     """Получает оценку пользователя из БД."""
#     try:
#         cursor = conn.cursor()
#         cursor.execute(
#             "SELECT score FROM search_results WHERE user_id = %s AND target_user_id = %s",
#             (user_id, target_user_id)
#         )
#         result = cursor.fetchone()
#         if result:
#             return result[0]
#         else:
#             return None
#     except Exception as e:
#         logging.error(f"Ошибка при получении оценки пользователя из БД: {e}")
#         return None



# @lru_cache(maxsize=128)
# def get_user_interests(user_id):
#     """Получает интересы пользователя (кешируется)."""
#     try:
#         user_info = get_vk_user_info(user_id, fields=['interests', 'music', 'books', 'groups'])
#         if not user_info:
#             return ''

#         interests = user_info.get('interests', '') + ' ' + user_info.get('music', '') + ' ' + user_info.get('books', '')
#         group_ids = user_info.get('groups', '')

#         if group_ids:
#             groups = ','.join(group_ids.split(','))
#         else:
#             groups = ''

#         interests += groups

#         return interests
#     except Exception as e:
#         logging.error(f"Ошибка при получении интересов пользователя: {e}")
#         return ''


# def calculate_interests_similarity(user1_interests, user2_interests):
#     """Вычисляет схожесть интересов через TF-IDF и косинусное сходство."""
#     try:
#         if not user1_interests.strip() or not user2_interests.strip():
#             return 0.0
#         tfidf_vectorizer = TfidfVectorizer()
#         tfidf_matrix = tfidf_vectorizer.fit_transform([user1_interests, user2_interests])
#         similarity_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
#         return similarity_score
#     except Exception as e:
#         logging.error(f"Ошибка при вычислении схожести интересов: {e}")
#         return 0.0


# async def fetch_friends(user_id):
#     """Асинхронно получает список друзей пользователя."""
#     try:
#         response = await asyncio.to_thread(vk_user.friends.get, user_id=user_id)
#         return response['items']
#     except vk_api.exceptions.ApiError as e:
#         logging.error(f"Ошибка при получении друзей пользователя {user_id}: {e}")
#         return []


# async def get_common_friends_count(user_id, target_user_id):
#     """Считает количество общих друзей между двумя пользователями."""
#     try:
#         friends1 = await fetch_friends(user_id)
#         friends2 = await fetch_friends(target_user_id)
#         common_friends = set(friends1) & set(friends2)
#         return len(common_friends)
#     except Exception as e:
#         logging.error(f"Ошибка при получении общих друзей: {e}")
#         return 0


##############################################################33
# было в главном цикле 
                            # scored_users = []
                            # for target_user in search_users:
                            #     score = evaluate_user(user_id, target_user, user_info, conn)

                            #     try:
                            #         cursor = conn.cursor()
                            #         cursor.execute(
                            #             "INSERT INTO search_results (user_id, target_user_id, score) VALUES (%s, %s, %s)",
                            #             (int(user_id), int(target_user['id']), float(score))
                            #         )
                            #         conn.commit()
                            #     except Exception as e:
                            #         logging.error(f"Ошибка при записи оценки пользователя в БД: {e}")
                            #         send_message(user_id, "Ошибка при записи оценки пользователя в БД.")  # Сообщение об ошибке

                                # scored_users.append((target_user, score))

                            # scored_users.sort(key=lambda x: x[1], reverse=True)

                            # current_search_results[user_id] = [user for user, score in scored_users]
                            # search_index[user_id] = 0

                        #     if current_search_results[user_id]:
                        #         target_user = current_search_results[user_id][0]
                        #         score = get_user_score(conn, user_id, target_user['id'])
                        #         if score is not None:
                        #             send_message(user_id,
                        #                          f"Найден первый пользователь: {target_user.get('first_name', 'Имя')} {target_user.get('last_name', 'Фамилия')}, Score: {score:.2f}",
                        #                          keyboard=create_keyboard_next_fav_black())
                        #         else:
                        #             send_message(user_id, "Ошибка при получении оценки пользователя.") # Сообщение об ошибке

                        #     else:
                        #         send_message(user_id, "Пользователи не найдены.")
                        #     if user_id in search_index:
                        #         del search_index[user_id]  #  Удаляем, если нет результатов
                        # except ValueError:
                        #     send_message(user_id, "Некорректный формат возраста.")
                        # except Exception as e:
                        #     logging.exception("Ошибка при обработке возраста:")

# Загрузка фото для карусели
"""
from pprint import pprint
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from functools import lru_cache
import sys
from pathlib import Path
import requests  # Импортируем модуль requests
import json
sys.path.append(str(Path(__file__).parent.parent))
from create_keyboard.create_keyboard import *
from psycopg2 import Error
from BD_tokens.BD_tokens import *
from config.config import *
from VKinder_db.create_db import *
from VKinder_db.models import *
import datetime
import logging
import vk_api

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Инициализация VK API
vk_session = vk_api.VkApi(token=TOKEN_GROUP)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session, group_id=GROUP_ID)

# Глобальные переменные для хранения состояния
user_states = {}            # Текущее состояние пользователей (FSM)
current_search_results = {} # Результаты поиска для каждого пользователя
search_index = {}           # Индекс текущего просматриваемого результата


def send_message(user_id, message, keyboard=None):
    """Отправляет сообщение пользователю в VK."""
    try:
        vk.messages.send(
            user_id=user_id,
            message=message,
            random_id=get_random_id(),
            keyboard=keyboard
        )
    except vk_api.exceptions.ApiError as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")


def get_vk_user_info(user_id, fields=None):
    """Получает информацию о пользователе VK."""
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
    """Вычисляет возраст по дате рождения."""
    try:
        birthdate = datetime.datetime.strptime(birthdate_str, '%d.%m.%Y')
        today = datetime.datetime.now()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        return age
    except (ValueError, TypeError):
        return None


def get_city_id(city_name):
    """Получает ID города по названию."""
    try:
        response = vk_user.database.getCities(q=city_name, count=1)
        if response['items']:
            return response['items'][0]['id']
        return None
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка при получении ID города: {e}")
        return None


def search_vk_users(user_info):
    """Ищет пользователей VK по заданным критериям."""
    try:
        global vk_user

        vk_session_user = vk_api.VkApi(token=check_token(user_info['user_id']))
        vk_user = vk_session_user.get_api()

        city_id = get_city_id(user_info['city'])

        params = {
            'city': city_id,
            'age_from': user_info['age_from'],
            'age_to': user_info['age_to'],
            'sex': user_info['sex'],
            'count': 10,
            'fields': 'city, sex, bdate, interests, music, books, groups, photo_200', # Добавлено photo_200 (или photo_400, photo_max)
            'status': 6  # В активном поиске
        }
        logging.info(f'params  {params}')
        response = vk_user.users.search(**params)
        users = response['items']
        logging.info(f"Найдено пользователей: {len(users)}")

        filtered_users = []
        for user_data in users:
            if get_blacklist(user_data['id']):
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


def handle_favorites_command(conn, user_id):
    """Добавляет текущего пользователя в избранное."""
    if user_id in current_search_results and search_index.get(user_id) is not None:
        target_user = current_search_results[user_id][search_index[user_id]]
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO favorites (user_id, favorite_user_id) VALUES (%s, %s)",
                (user_id, target_user['id'])
            )
            conn.commit()
            send_message(user_id, f"Пользователь {target_user.get('first_name', 'Имя')} {target_user.get('last_name', 'Фамилия')} добавлен в избранное.")
        except Error as e:
            logging.error(f"Ошибка при добавлении в избранное: {e}")
            conn.rollback()
            send_message(user_id, "Ошибка при добавлении в избранное.")
    else:
        send_message(user_id, "Сначала начните поиск, введя команду 'начать'.")


def handle_show_favorites_command(conn, user_id):
    """Показывает список избранных пользователей."""
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
    """Добавляет текущего пользователя в черный список."""
    if user_id in current_search_results and search_index.get(user_id) is not None:
        target_user = current_search_results[user_id][search_index[user_id]]
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO blacklist (user_id, blacklisted_user_id) VALUES (%s, %s)",
                (user_id, target_user['id'])
            )
            conn.commit()
            send_message(user_id, f"Пользователь {target_user.get('first_name', 'Имя')} {target_user.get('last_name', 'Фамилия')} добавлен в черный список.")
        except Error as e:
            logging.error(f"Ошибка при добавлении в черный список: {e}")
            conn.rollback()
            send_message(user_id, "Ошибка при добавлении в черный список.")
    else:
        send_message(user_id, "Сначала начните поиск, введя команду 'начать'.")


def add_user_db(vk_user_info):
    """Обрабатывает и сохраняет данные пользователя VK в базу данных."""
    try:
        vk_id = int(vk_user_info['id'])
        first_name = str(vk_user_info.get('first_name', ''))[:20]
        if not first_name:
            first_name = 'Неизвестно'

        city = 'Не указан'
        if 'city' in vk_user_info:
            if isinstance(vk_user_info['city'], dict):
                city = vk_user_info['city'].get('title', 'Не указан')
            else:
                city = str(vk_user_info['city'])

        age = 0  # Значение по умолчанию
        if 'bdate' in vk_user_info and vk_user_info['bdate']:
            bdate_parts = vk_user_info['bdate'].split('.')
            if len(bdate_parts) == 3:  # Полная дата (день.месяц.год)
                try:
                    age = calculate_age(vk_user_info['bdate']) or 0
                except Exception as e:
                    logging.warning(f"Ошибка вычисления возраста: {e}")
            else:
                logging.info(f"Пользователь {vk_id}: указана неполная дата рождения")

        sex = str(vk_user_info.get('sex', 0))
        if sex == '1':
            sex = 'женщина'
        elif sex == '2':
            sex = 'мужчина'
        else:
            sex = 'не известный'
        sex = sex[:10]

        result = add_user(
            vk_id=vk_id,
            first_name=first_name,
            age=age,
            sex=sex,
            city=city
        )
        logging.info(result)
    except Exception as e:
        logging.info(f'Ошибка в добавление данных пользователя{e}')


def get_image_id_from_photo(vk, photo_url):
    """Загружает фото на сервер VK и получает image_id"""
    try:
        photo = requests.get(photo_url, stream=True).raw
        upload_server = vk.photos.getMessagesUploadServer(album_id=600000001)['upload_url']  # Укажите album_id, чтобы сохранять в альбом сообщений
        response = requests.post(upload_server, files={'photo': photo})
        data = json.loads(response.text)
        saved_photo = vk.photos.saveMessagesPhoto(
            server=data['server'],
            photo=data['photo'],
            hash=data['hash'],
            album_id=600000001  # Укажите album_id
        )[0]  #  Важно: получаем список, берем первый элемент (словарь)
        return saved_photo['id']  # Возвращаем photo_id  (image_id для карусели)
    except Exception as e:
        logging.error(f"Ошибка при загрузке фото: {e}")
        return None


def create_carousel_from_users(users_list, vk):
    elements = []
    for user in users_list:
        # Проверяем, есть ли вообще фотография
        photo_url = user.get('photo_200')  # Или photo_400, или photo_max - в зависимости от полей, которые вы получаете из API
        if photo_url:
            image_id = get_image_id_from_photo(vk, photo_url)  # Получаем image_id

            if image_id:  # Проверяем, что загрузка прошла успешно
                elements.append({
                    "title": f"{user['first_name']} {user['last_name']}",
                    "description": "Описание пользователя",
                    "image_id": image_id,  # Используем полученный image_id
                    "buttons": [
                        {
                            "action": {
                                "type": "text",
                                "label": "Подробнее"
                            }
                        }
                    ]
                })
            else:
                logging.warning(f"Не удалось загрузить фото для пользователя {user.get('first_name', '')} {user.get('last_name', '')}.")  # Логируем, если не удалось загрузить фото
        else:
            logging.warning(f"У пользователя {user.get('first_name', '')} {user.get('last_name', '')} нет фото.")  # Логируем, если у пользователя нет фото

    return {"elements": elements}


def send_carousel_to_user(user_id, users_list, vk):
    """Отправляет карусель с пользователями указанному user_id"""
    try:
        # Создаем карусель
        carousel_template = create_carousel_from_users(users_list, vk)

        if carousel_template['elements']:
            vk.messages.send(
                user_id=user_id,
                message="Подходящие анкеты:",
                template=json.dumps(carousel_template),
                random_id=random.randint(1, 10000)
            )

        return True
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка при отправке карусели: {e}")
        return False


def main():
    """Основная функция бота: инициализирует БД и запускает бесконечный цикл."""
    conn = connect_db()
    if not conn:
        raise RuntimeError("Не удалось подключиться к базе данных")
    create_tables(conn)
    global current_search_results, search_index
    try:
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
                user_id = event.user_id
                message_text = event.text.lower()

                vk_user_info = get_vk_user_info(user_id, fields=['first_name', 'city', 'bdate', 'sex'])
                if vk_user_info:
                    add_user_db(vk_user_info)

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

                            user_info = {"user_id": user_id, "age_from": age_from, "age_to": age_to,
                                         "sex": user_data["sex"], "city": user_data["city"]}
                            search_users = search_vk_users(user_info)

                            send_carousel_to_user(user_id, search_users, vk)

                        except Exception as e:
                            print(f'ошибка {e}')

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
    """


"""
Проблема с кнопкой “далее”:
При нажатии на кнопку “далее”, перебрасывает на выбор возраста. Это говорит о том, что состояние бота (FSM) сбрасывается или не сохраняется правильно при нажатии кнопки “далее”.
Причины и решения:
1.Убедиться, что в основном цикле main() есть обработка сообщения message_text == 'дальше'. Этот блок кода должен обновлять индекс текущего просматриваемого результата и отправлять следующую анкету.
elif message_text == 'дальше':
    handle_next_command(user_id, vk) 
2.Создать функцию handle_next_command, которая будет выполнять следующие действия:

Увеличивать индекс search_index[user_id].
Проверять, не достигнут ли конец списка результатов.
Отправлять следующую анкету пользователю.
Обрабатывать случай, когда достигнут конец списка результатов (например, отправлять сообщение “Больше нет анкет” или начинать новый поиск).

3.Потеря состояния:
Убедиться, что состояние пользователя (user_states[user_id]) не сбрасывается при нажатии кнопки “далее”. Возможно, где-то в коде вы случайно удаляется или перезаписывается состояние пользователя.

Решение: 
1. Создать (или измените) функцию handle_next_command:
def handle_next_command(user_id, vk):
    """Отправляет следующую анкету пользователю."""
    global current_search_results, search_index

    if user_id in current_search_results:
        results = current_search_results[user_id]
        if results:
            current_index = search_index.get(user_id, 0)  # Получаем текущий индекс или 0, если его нет
            current_index += 1  # Увеличиваем индекс

            if current_index < len(results):  # Если индекс не вышел за границы списка
                search_index[user_id] = current_index  # Обновляем индекс

                send_carousel_to_user(user_id, [results[current_index]], vk)  # Отправляем карусель с одной анкетой
            else:
                send_message(user_id, "Больше нет анкет.", keyboard=create_keyboard_start())  # Сообщаем, что анкеты закончились
                # Дополнительно: Можно предложить начать новый поиск
                user_states[user_id] = None  # Сбрасываем состояние
                del current_search_results[user_id]
                del search_index[user_id]
        else:
            send_message(user_id, "Нет результатов поиска.", keyboard=create_keyboard_start())  # Сообщаем, что нет результатов поиска
    else:
        send_message(user_id, "Сначала начните поиск, введя команду 'начать'.", keyboard=create_keyboard_start())  # Сообщаем, что нужно начать поиск

2. Добавить вызов handle_next_command в main():
        elif message_text == 'дальше':
    handle_next_command(user_id, vk)

3. Сохранить результаты поиска в current_search_results и инициализировать search_index:

В коде, где вызываем send_carousel_to_user после получения результатов поиска, сохранить результаты поиска в current_search_results и инициализировать search_index:
search_users = search_vk_users(user_info)
current_search_results[user_id] = search_users  # Сохраняем результаты поиска
search_index[user_id] = 0  # Инициализируем индекс
send_carousel_to_user(user_id, [search_users[0]], vk) # Отправляем первую анкету

4. Отправлять клавиатуру с кнопкой “далее” вместе с каждой анкетой:

Изменить функцию send_carousel_to_user, чтобы она всегда отправляла клавиатуру с кнопкой “далее”:
def send_carousel_to_user(user_id, users_list, vk):
    """Отправляет карусель с пользователями указанному user_id"""
    try:
        # Создаем карусель
        carousel_template = create_carousel_from_users(users_list, vk)

        if carousel_template['elements']:
            keyboard = create_keyboard_next()  # Создаем клавиатуру с кнопкой "далее"
            vk.messages.send(
                user_id=user_id,
                message="Подходящие анкеты:",
                template=json.dumps(carousel_template),
                random_id=random.randint(1, 10000),
                keyboard=keyboard # Отправляем клавиатуру
            )
        else:
            send_message(user_id, "Нет подходящих анкет.", keyboard=create_keyboard_start())  # Отправляем сообщение, если нет анкет

        return True
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка при отправке карусели: {e}")
        return False

5. Создать функцию create_keyboard_next() в модуле create_keyboard:
from vk_api.keyboard import VkKeyboard, VkKeyboardButton, KeyboardButtonColor

def create_keyboard_next():
    keyboard = VkKeyboard(one_time=False) # False, чтобы клавиатура не исчезала после нажатия

    keyboard.add_button(label="Дальше", color=KeyboardButtonColor.PRIMARY) # Меняем цвет
    return keyboard.get_keyboard()
    
