import json
import json
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from bot import *



def create_keyboard_start():
    """
    Создает клавиатуру с кнопкой "Начать".
    """
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Начать", color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()

def create_keyboard_city():
    """
    Создает клавиатуру с выбором города и постоянными кнопками.
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
    Создает клавиатуру с выбором пола и постоянными кнопками.
    """
    keyboard = VkKeyboard(one_time=True)
    
    keyboard.add_button("Женский")
    keyboard.add_button("Мужской")
    keyboard.add_line()
    keyboard.add_button("Не важно")
    return keyboard.get_keyboard()

def create_favorites_keyboard():
    """Создает клавиатуру для работы с избранными"""
    keyboard = {
        "inline": True,
        "buttons": [
            [
                {
                    "action": {
                        "type": "callback",
                        "label": "⭐ Вывести избранные",
                        "payload": {"action": "show_favorites"}
                    },
                    "color": "positive"
                },
                {
                    "action": {
                        "type": "callback",
                        "label": "🚫 Вывести ЧС",
                        "payload": {"action": "show_blacklist"}
                    },
                    "color": "negative"
                }
            ],
        
        ]
    }
    return json.dumps(keyboard)


def remove_from_blacklist(bl_id):
    '''УДалитть из черного списка'''
    keyboard = {
                "inline": True,
                "buttons": [
                    [
                        {
                            "action": {
                                "type": "callback",
                                "label": "❌ Удалить из ЧС",
                                "payload": {
                                    "action": "remove_from_blacklist",
                                    "user_id": bl_id
                                }
                            },
                            "color": "negative"
                        }
                    ]
                ]
            }
    return keyboard

def questionnaire_keyboard(user, current_index ):
    '''Кнопки для анкеты'''
    profile_keyboard = {
            "inline": True,
            "buttons": [
                [
                    {
                        "action": {
                            "type": "callback",
                            "label": "❤️ Добавить в избранное",
                            "payload": {
                                "user_id": user['id'],
                                "action": "add_favorite",
                                "current_index": current_index
                            }
                        },
                        "color": "positive"
                    },
                    {
                        "action": {
                            "type": "callback",
                            "label": "🚫 Добавить в ЧС",
                            "payload": {
                                "user_id": user['id'],
                                "action": "add_blacklist",
                                "current_index": current_index
                            }
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
                            "type": "callback",
                            "label": "➡️ Далее",
                            "payload": {
                                "action": "next_profile",
                                "current_index": current_index
                            }
                        },
                        "color": "primary"
                    }
                ]
            ]
        }
    return profile_keyboard

def keyboard_favorites_list(user_id, fav_id):
    """Клавиатура для избранного списка (исправленная)"""
    keyboard = {
        "inline": True,
        "buttons": [
            [  # Первый ряд - 2 кнопки действий
                {
                    "action": {
                        "type": "callback",
                        "label": "❌ Удалить",
                        "payload": {
                            "action": "remove_from_favorites",
                            "user_id": fav_id
                        }
                    },
                    "color": "negative"
                },
                {
                    "action": {
                        "type": "callback",
                        "label": "🚫 В ЧС",
                        "payload": {
                            "action": "add_blacklist",
                            "user_id": fav_id
                        }
                    },
                    "color": "primary"
                }
            ],
            [  # Второй ряд - 1 кнопка с ссылкой
                {
                    "action": {
                        "type": "open_link",
                        "label": "✉️ Написать сообщение",
                        "link": f"https://vk.com/im?sel={fav_id}"
                    }
                }
            ]
        ]
    }
    return keyboard