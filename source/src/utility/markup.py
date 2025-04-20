from telebot.util import quick_markup
from telebot.types import InlineKeyboardMarkup
from telebot.types import ReplyKeyboardMarkup, KeyboardButton


def setup_markup(items: list | dict, reverse: bool = False):
    markup_dict = {}
    if isinstance(items, list):
        for item in items:
            markup_dict[item] = {"callback_data": item}
    elif isinstance(items, dict) and not reverse:
        for key, value in items.items():
            markup_dict[key] = {"callback_data": value}
    elif isinstance(items, dict) and reverse:
        for key, value in items.items():
            markup_dict[value] = {"callback_data": key}
    return markup_dict

def setup_button(buttons: list):
    return [KeyboardButton(label) for label in buttons]


def keyboard_markup(
    value: list | dict, row_width: int = 2, reverse: bool = False
) -> InlineKeyboardMarkup:
    return quick_markup(setup_markup(value, reverse), row_width)


def checkbox_markup(
    checkbox_states: dict, row_width: int = 1, reverse: bool = False
) -> InlineKeyboardMarkup:
    return quick_markup(setup_markup(checkbox_states, reverse), row_width)


def reply_markup_button(buttons: list):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for i in range(0, len(setup_button(buttons)), 2):
        markup.add(*buttons[i : i + 2])
    return markup
