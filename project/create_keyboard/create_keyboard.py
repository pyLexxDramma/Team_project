
import json
import requests
from io import BytesIO
from PIL import Image
import json
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import sys
import vk_api

from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))  # Путь до папки project
# Затем импортируйте:
from bot.bot import calculate_age


def create_keyboard_start():
    """
    Создает клавиатуру с кнопкой "Начать".
    Returns:
        dict: Готовая клавиатура для VK API.
    """
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Начать", color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()

def create_keyboard_city():
    """
    Создает клавиатуру с выбором города.
    Returns:
        dict: Готовая клавиатура для VK API.
    """
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Москва")
    keyboard.add_button("Санкт-Петербург")
    keyboard.add_line()
    keyboard.add_button("Ижевск")
    keyboard.add_button("Другой")
    return keyboard.get_keyboard()

def create_keyboard_sex():
    """
    Создает клавиатуру с выбором пола.
    Returns:
        dict: Готовая клавиатура для VK API.
    """
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Женский")
    keyboard.add_button("Мужской")
    keyboard.add_line()
    keyboard.add_button("Не важно")
    return keyboard.get_keyboard()

def create_keyboard_next_fav_black():
    """
    Создает клавиатуру с кнопками "Дальше", "Избранное", "Черный список".
    Returns:
        dict: Готовая клавиатура для VK API.
    """
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Дальше", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("Избранное", color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button("Черный список", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()


def create_carousel_from_users(users_list, vk):
    """Создает карусель из списка пользователей с обработкой фото"""
    carousel_elements = []
    
    for user in users_list:
        try:
            # Основная информация
            user_id = user.get('id')
            first_name = user.get('first_name', '')
            last_name = user.get('last_name', '')
            age = calculate_age(user.get('bdate', '')) if user.get('bdate') else None
            city = user.get('city', {}).get('title', 'Город не указан')
            
            # Получаем фото и обрабатываем его
            photo_id = None
            if user.get('crop_photo') and user['crop_photo'].get('photo'):
                photo = user['crop_photo']['photo']
                
                # 1. Попробуем использовать оригинальное фото с обрезкой
                try:
                    photo_id = f"{photo['owner_id']}_{photo['id']}"
                    
                    # Проверяем доступность фото через API
                    photo_info = vk.photos.getById(photos=photo_id)
                    if not photo_info:
                        photo_id = None
                except:
                    photo_id = None
                
                # 2. Если не получилось, загружаем и обрабатываем изображение
                if not photo_id:
                    try:
                        # Выбираем максимальное доступное изображение
                        best_size = max(
                            [s for s in photo['sizes'] if s['type'] in ['x', 'y', 'z']],
                            key=lambda x: x['width'] * x['height'],
                            default=None
                        )
                        
                        if best_size:
                            # Скачиваем изображение
                            response = requests.get(best_size['url'])
                            img = Image.open(BytesIO(response.content))
                            
                            # Обрезаем до соотношения 13:8
                            width, height = img.size
                            target_ratio = 13/8
                            
                            if width/height > target_ratio:
                                # Обрезаем по ширине
                                new_width = int(height * target_ratio)
                                left = (width - new_width) // 2
                                img = img.crop((left, 0, left + new_width, height))
                            else:
                                # Обрезаем по высоте
                                new_height = int(width / target_ratio)
                                top = (height - new_height) // 2
                                img = img.crop((0, top, width, top + new_height))
                            
                            # Сохраняем во временный файл
                            temp_img = BytesIO()
                            img.save(temp_img, format='JPEG')
                            temp_img.seek(0)
                            
                            # Загружаем на сервер VK
                            upload_url = vk.photos.getMessagesUploadServer()['upload_url']
                            response = requests.post(upload_url, files={'photo': temp_img}).json()
                            save_result = vk.photos.saveMessagesPhoto(
                                photo=response['photo'],
                                server=response['server'],
                                hash=response['hash']
                            )
                            
                            photo_id = f"{save_result[0]['owner_id']}_{save_result[0]['id']}"
                    except Exception as e:
                        print(f"Ошибка обработки фото: {e}")
            
            # Формируем элемент карусели
            element = {
                "title": f"{first_name} {last_name}"[:80],
                "description": f"{age} лет, {city}"[:80] if age else city[:80],
                "buttons": [
                    {
                        "action": {
                            "type": "text",
                            "label": "❤️ В избранное",
                            "payload": json.dumps({"type": "add_favorite", "user_id": user_id})
                        }
                    },
                    {
                        "action": {
                            "type": "open_link",
                            "label": "🔍 Профиль",
                            "link": f"https://vk.com/id{user_id}"
                        }
                    },
                    {
                        "action": {
                            "type": "text",
                            "label": "🚫 В ЧС",
                            "payload": json.dumps({"type": "add_blacklist", "user_id": user_id})
                        }
                    }
                ],
                "action": {
                    "type": "open_link",
                    "link": f"https://vk.com/id{user_id}"
                }
            }
            
            if photo_id:
                element["photo_id"] = photo_id
            
            carousel_elements.append(element)
            
        except Exception as e:
            print(f"Ошибка обработки пользователя {user_id}: {e}")
            continue
    
    return {
        "type": "carousel",
        "elements": carousel_elements[:10]
    }

