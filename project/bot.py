from create_keyboard import *
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
from pprint import pprint
from create_db import *
from BD_tokens import *
from config import *
from models import* 
import datetime
import logging
import vk_api
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Инициализация VK API
vk_session = vk_api.VkApi(token=TOKEN_GROUP) 
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID)

# Глобальные переменные для хранения состояния
user_states = {}            # Текущее состояние пользователей (FSM)
current_search_results = {} # Результаты поиска для каждого пользователя
search_index = {}           # Индекс текущего просматриваемого результата

def send_message(user_id, message, keyboard=None):
    """Отправляет сообщение пользователю в VK
    
    :param user_id: ID пользователя
    :param message: Текст сообщения
    :param keyboard: Клавиатура (None - без клавиатуры)
    """
    params = {
        'user_id': user_id,
        'message': message,
        'random_id': get_random_id()
    }

    if keyboard is not None:
        params['keyboard'] = keyboard.get_keyboard() if hasattr(keyboard, 'get_keyboard') else keyboard

    vk.messages.send(**params)



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
    except vk_api.exceptions.ApiError as e:
        logging.error(f"Ошибка обработке возраста: {e}")
        
        return None


def get_city_id(city_name):
    """Получает ID города по названию."""
    try:
        response = vk_user.database.getCities(q=city_name, count=1)
        if response['items']:
            return response['items'][0]['id']
        return None
    except vk_api.exceptions.ApiError as e:
        logging.error(f"Ошибка при получении ID города: {e}")
        return None


def search_vk_users(user_id, user_info):
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
        send_message(user_id, f"Найдено пользователей: {len(users)}, подождите пару секунд, анкеты формируются!")

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
                except vk_api.exceptions.ApiError as e:
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
    except vk_api.exceptions.ApiError as e:
        logging.info(f'Ошибка в добавление данных пользователя{e}')


def photo_search(id_recommendations, count=100):
    try:
        photos = vk_user.photos.get(
                owner_id=id_recommendations,
                album_id='profile',  
                count=count,
                photo_sizes=0,      
                extended=1 
            )
        return photos['items']
    
    except vk_api.exceptions.ApiError as e:
        logging.error(f"Ошибка при получении фото для {id_recommendations}: {e}")
        return None
    
    
def photo_filtering(user_id, id_recommendations, count=3):
    
    all_photo = photo_search(id_recommendations)
    if not all_photo:
        send_message(user_id, f'У пользователя нет фото')
    
    sorted_photos = sorted(
        all_photo,
        key=lambda x: x['likes']['count'],
        reverse=True)
    
    top_photos = []
    for photo in sorted_photos[:count]:
        top_photos.append({
            'owner_id': photo['owner_id'],
            'id': photo['id'],
        })

    return top_photos
    

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

        id_recommendations = user.get('id') 

        result = photo_filtering(user_id, id_recommendations)
        
        # Получаем фотографии
        attachments = []
        if result:
            for photo in result:
                photo_str = f"photo{photo['owner_id']}_{photo['id']}_{token}"
                attachments.append(photo_str)
        
        
        profile_keyboard = questionnaire_keyboard(user, current_index)
        # Клавиатура управления избранными
        favorites_keyboard = json.loads(create_favorites_keyboard())
               
        # Объединяем все клавиатуры
        combined_keyboard = {
            "one_time": False,
            "inline": True,
            "buttons": (
                profile_keyboard["buttons"] + 
                favorites_keyboard["buttons"]
            )
        }
        # Подготавливаем параметры отправки
        params = {
            'user_id': user_id,
            'message': message,
            'random_id': get_random_id(),
            'keyboard': json.dumps(combined_keyboard)
        }
        
        if attachments:
            params['attachment'] = ",".join(attachments)
        
        vk.messages.send(**params)
        
    except vk_api.exceptions.ApiError as e:
        logging.error(f"Ошибка при отправке профиля: {e}")
        send_message(user_id, "Произошла ошибка при загрузке анкеты.")


def show_favorites_simple(user_id):
    """Выводит список избранных пользователей"""
    try:
        favorites = get_favourite(user_id)
        
        if isinstance(favorites, str) and favorites.startswith('Ошибка'):
            send_message(user_id, favorites)
            return
        
        if not favorites:
            send_message(user_id, "Ваш список избранных пока пуст.")
            return
        
        message = "⭐ Ваши избранные:\n\n"
        for i, (first_name, last_name, fav_id) in enumerate(favorites, 1):
            message += f"{i}. {first_name} {last_name}\n"
            message += f"   👉 vk.com/id{fav_id}\n\n"
        
        send_message(user_id, message.strip())
        
    except vk_api.exceptions.ApiError as e:
        logging.error(f"Ошибка при выводе избранных: {e}")
        send_message(user_id, "Произошла ошибка при загрузке списка избранных.")

def show_blacklist(user_id):
    '''Выводит черный список '''
    try:
        # Получаем данные из БД
        blacklist = get_blacklist(user_id)
        
        if isinstance(blacklist, str) and blacklist.startswith('Ошибка'):
            send_message(user_id, blacklist)
            
        if not blacklist:
            send_message(user_id, "Ваш черный список пуст.")
            
        # Формируем сообщение
        send_message(user_id, "🚫 Ваш черный список:")

        for i, (first_name, last_name, bl_id) in enumerate(blacklist, 1):
            # Формируем сообщение для одной анкеты
            message = f"{i}. {first_name} {last_name}\n"
            message += f"👉 vk.com/id{bl_id}"
         # Создаем клавиатуру с кнопкой удаления
            keyboard = remove_from_blacklist(bl_id)
            
            # Отправляем анкету
            send_message(user_id, message, keyboard=json.dumps(keyboard))
            
    except vk_api.exceptions.ApiError as e:
        logging.error(f"Ошибка при выводе ЧС: {e}")
        send_message(user_id, "Произошла ошибка при загрузке чёрного списка.")







def main():
    """Основная функция бота: инициализирует БД и запускает бесконечный цикл."""
    conn = connect_db()
    if not conn:
        raise RuntimeError("Не удалось подключиться к базе данных")
    create_tables(conn)
    
    try:
        for event in longpoll.listen():
            # Обработка нажатий inline-кнопок
            if event.type == VkBotEventType.MESSAGE_EVENT:
                try:
                    payload = event.obj.get('payload')
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    elif not isinstance(payload, dict):
                        raise ValueError("Некорректный формат payload")
                        
                    user_id = event.obj['user_id']
                    
                    # Обработка добавления в избранное
                    if payload.get('action') == 'add_favorite':
                        if user_id in current_search_results:
                            current_index = payload.get('current_index', 0)
                            target_user = current_search_results[user_id][current_index]

                            try:
                                vk_id = target_user['id']
                                first_name = target_user['first_name']
                                last_name = target_user.get('last_name', '')
                                add_favourite(vk_id, first_name, last_name, user_id)
                                send_message(user_id, f"❤️ {first_name} {last_name} добавлен(а) в избранное!")
                            
                            except vk_api.exceptions.ApiError as e:
                                logging.error(f"Ошибка при добавлении в избранное: {e}")
                                conn.rollback()
                    
                    # Обработка добавления в черный список
                    elif payload.get('action') == 'add_blacklist':
                       
                        if user_id in current_search_results:
                            current_index = payload.get('current_index', 0)
                            target_user = current_search_results[user_id][current_index]

                            try:
                                vk_id = target_user['id']
                                first_name = target_user['first_name']
                                last_name = target_user.get('last_name', '')
                                
                                add_blacklist(vk_id, first_name, last_name, user_id)
                                send_message(user_id,
                                    f"🚫 {target_user['first_name']} добавлен(а) в черный список!")
                           
                            except vk_api.exceptions.ApiError as e:
                                logging.error(f"Ошибка при добавлении в ЧС: {e}")
                                conn.rollback()
                    
                    # Обработка кнопки "Далее"
                    elif payload.get('action') == 'next_profile':
                        # Проверяем есть ли результаты поиска
                        try: 
                            if user_id not in current_search_results:
                                send_message(user_id, "Сначала выполните поиск!")
                                continue
                            # Увеличиваем индекс
                            current_index = search_index.get(user_id, 0) + 1
                            # Проверяем есть ли еще анкеты
                            if current_index < len(current_search_results[user_id]):
                                # Обновляем индекс и показываем следующую анкету
                                search_index[user_id] = current_index
                                send_user_profile(user_id, current_search_results[user_id], current_index)
                            else:
                                # Анкеты закончились
                                send_message(user_id, "Анкеты закончились! Напишите 'Начать' для нового поиска.")
                                # Очищаем результаты поиска
                                del current_search_results[user_id]
                                del search_index[user_id]
                        except vk_api.exceptions.ApiError as e:
                            print(f'Ошибка обработки анкет {e}')
                    
                    # Вывести списко избранных
                    elif payload.get('action') == 'show_favorites':
                        try: 
                            show_favorites_simple(user_id)
                            continue
                        except vk_api.exceptions.ApiError as e:
                            print(f'Ошибка при выводе списка избранных {e}')
                    
                    # вывести черный список
                    elif payload.get('action') == 'show_blacklist':
                        try: 
                            show_blacklist(user_id)
                            continue
                        except vk_api.exceptions.ApiError as e:
                            logging.error(f'Ошибка при выводе черного списка {e}')
                            
                    # удаляет из черного списка
                    elif payload.get('action') == 'remove_from_blacklist':
                
                        try :
                            vk_id = payload['user_id']  # ID пользователя, которого нужно удалить из ЧС
                            user_id = event.obj['user_id']  # ID пользователя, который нажал кнопку

                            result = delete_blacklist(vk_id, user_id)
                            
                            if result.startswith('Успешно'):
                                send_message(user_id, result)
                            else:
                                send_message(user_id, f"Ошибка: {result}")
                                
                        except vk_api.exceptions.ApiError as e:
                            logging.error(f"Ошибка удаления из ЧС: {e}")
                            send_message(user_id, "Произошла ошибка при удалении из чёрного списка")
                        

                except vk_api.exceptions.ApiError as e:
                    logging.error(f"Ошибка обработки: {e}")
                    send_message(user_id, "⚠️ Произошла ошибка. Попробуйте ещё раз.")
                
            # Обработка обычных сообщений
            if event.type == VkBotEventType.MESSAGE_NEW and event.from_user and event.message.get('text'):
                user_id = event.message['from_id']
                message_text = event.message['text'].lower().strip()
                
                # Получаем информацию о пользователе
                if not user_states.get(user_id):
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
                        
                        user_states[user_id] = None  # Сбрасываем состояние
                    
                        user_info = {
                            "user_id": user_id,
                            "age_from": age_from,
                            "age_to": age_to,
                            "sex": user_data["sex"],
                            "city": user_data["city"]
                        }
                        
                        list_users = search_vk_users(user_id, user_info)
                        if list_users:
                            current_search_results[user_id] = list_users
                            search_index[user_id] = 0
                            send_user_profile(user_id, list_users)
                        else:
                            send_message(user_id, "По вашему запросу ничего не найдено. Попробуйте другие критерии.")
                            user_states[user_id] = None  # Сбрасываем состояние
                                       
                    except ValueError:
                        send_message(user_id, "Пожалуйста, введите возраст числом или диапазон (например 25-30)")
        
    except vk_api.exceptions.ApiError as e:
        logging.exception(f"Ошибка в основном цикле: {e}")

            
if __name__ == '__main__':
    print('Бот запущен !')
    main()


# Возможные проблемы:
# 1 у пользователя может быть скрыты дата рождения, или может быть видно только день и месяц, и мы не сможем его добавить в базу данных, если  мы уберем 
# огранечение в таблице user что у нас возраст может быть нулевым значением, либо если мы не можем вычеслит возраст то можем по дефолту ставить просто ноль


# 2 доработать когда пользователь хочет вввести другой город 

# 3 при выводе людей не срабатывает обработка если мы человека уже добавли в чс 

# 4 если ЧС пуста то надо написать что список пуст 

# 5 реализовать вывод избранный по одному, и добавить какие то кнопки для взаимодейстяви,
# предлогаю кнопку удалть из избранного, и добавить в ЧС(при добавление в чс удаляется из избранного 
# избежать то го что человек в избранном и чс)
