from vk_api.keyboard import VkKeyboard, VkKeyboardColor


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
