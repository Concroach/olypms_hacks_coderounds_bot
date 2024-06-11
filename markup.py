"""Тут inline-кнопки, меню"""
import asyncio
from aiogram import types

from db import Database

db = Database()

asyncio.get_event_loop().run_until_complete(db.async_init())

# ответы бота на кнопки меню
menu_answers = {
    "Олимпиады": "Вы во вкладке 'Олимпиады'",
    "Выключить рассылку олимпиад": "❌ Рассылка олимпиад выключена",
    "Включить рассылку олимпиад": "✅ Рассылка олимпиад включена",
    "Хакатоны": "Вы во вкладке 'Хакатоны'",
    "Программирование": "Вы во вкладке 'Программирование'",
    "Контесты": "Здесь Вы можете отслеживать контесты с разных платформ",
    "Выключить рассылку хакатонов": "❌ Рассылка хакатонов выключена",
    "Включить рассылку хакатонов": "✅ Рассылка хакатонов включена",
    "Настройки": "Вы в настройках",
    "Вернуться в меню 'Программирование'": "Вы во вкладке 'Программирование'",
    "Вернуться в главное меню": "Вы в главном меню",
    "Выключить рассылку": "❌ Рассылка выключена",
    "Включить рассылку": "✅ Рассылка включена",
}


"""Меню"""
# главное меню
async def create_main_menu():
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_olymp = types.KeyboardButton("Олимпиады")
    btn_hacks = types.KeyboardButton("Хакатоны")
    btn_prog = types.KeyboardButton("Программирование")
    btn_sett = types.KeyboardButton("Настройки")
    btn_ts = types.KeyboardButton("Тех поддержка")
    menu.add(btn_olymp, btn_hacks, btn_prog, btn_sett, btn_ts)
    return menu


# меню олимпииад
async def create_olympiads_menu(chat_id):
    if await db.check_teacher_status(chat_id):
        btn_list = types.KeyboardButton("Измeнить класс") # первая е - английская
    else:
        btn_list = types.KeyboardButton("Измeнить предметы") # первая е - английская
    btn_list_camps = types.KeyboardButton("Список лагерей")
    # текст кнопки для рассылки (включить/выключить вза)
    text_btn_mailing = "Включить рассылку олимпиад"
    if await db.get_mailing_olympiads_state(chat_id) is True:
        text_btn_mailing = "Выключить рассылку олимпиад"
    btn_mailing = types.KeyboardButton(text_btn_mailing)
    btn_remind = types.KeyboardButton("Напоминать 🔔")
    btn_back = types.KeyboardButton("Вернуться в главное меню")
    kb = [[btn_list, btn_list_camps, btn_mailing], [btn_remind], [btn_back]]
    menu = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    return menu


# меню хакатонов
async def create_hackathons_menu(chat_id):
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_list = types.KeyboardButton("Список хакатонов")
    # текст кнопки для рассылки (включить/выключить вза)
    text_btn_mailing = "Включить рассылку хакатонов"
    if await db.get_mailing_hackathons_state(chat_id) is True:
        text_btn_mailing = "Выключить рассылку хакатонов"
    btn_mailing = types.KeyboardButton(text_btn_mailing)
    btn_back = types.KeyboardButton("Вернуться в главное меню")
    menu.add(btn_list, btn_mailing, btn_back)
    return menu


# меню программироввания
async def create_prog_menu(chat_id):
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_training = types.KeyboardButton("Контесты")
    btn_world = types.KeyboardButton("Международные олимпиaды")
    btn_mailing = types.KeyboardButton("Включить рассылку")
    if await db.get_mailing_status_of_programming(chat_id) is True:
        btn_mailing = types.KeyboardButton("Выключить рассылку")
    btn_back = types.KeyboardButton("Вернуться в главное меню")
    menu.add(btn_training, btn_world, btn_mailing, btn_back)
    return menu


# меню программироввания
async def create_training_menu(chat_id):
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_codeforces = types.KeyboardButton("Codeforces")
    btn_leetcode = types.KeyboardButton("LeetCode")
    btn_codefchef = types.KeyboardButton("CodeChef")
    btn_back = types.KeyboardButton("Вернуться в меню 'Программирование'")
    menu.add(btn_codeforces, btn_leetcode, btn_codefchef, btn_back)
    return menu

# меню настроек
async def create_settings_menu():
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Изменить класс")
    btn2 = types.KeyboardButton("Изменить предметы")
    btn3 = types.KeyboardButton("Вернуться в главное меню")
    menu.add(btn1, btn2, btn3)
    return menu

# inline-кнопки для выбора класса
async def create_class_markup_for_teacher(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    classes = ["8", "9", "10", "11"]
    for cl in classes:
        markup.add(types.InlineKeyboardButton(text=f"{'✅' if await db.get_class(chat_id, cl) else ''} {cl}", callback_data=cl))
    return markup

"""Inline-кнопки"""
# inline-кнопки для выбора класса
async def create_class_markup(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    classes = ["8", "9", "10", "11", "Не школьник", "Учитель"]
    for cl in classes:
        markup.add(types.InlineKeyboardButton(text=f"{'✅' if await db.get_class(chat_id, cl) else ''} {cl}", callback_data=cl))
    return markup


# inline-кнопки для выбора предметов
async def create_subjects_markup(chat_id, subject_names):
    markup = types.InlineKeyboardMarkup()
    subjects = subject_names.copy()
    cnt = 0  # счетчик, чтобы разбить предметы на 3 столбца
    arr = []
    for subj in subjects:
        if subj == "Генетика":  # без генетики
            continue
        arr.append(types.InlineKeyboardButton(text=f"{'✅' if await db.get_sub(chat_id, subj) else ''} {subj}", callback_data=subj))
        cnt += 1
        if cnt == 3:
            markup.row(*arr)
            arr = []
            cnt = 0
    arr.append(types.InlineKeyboardButton(text="Готово", callback_data='done'))
    if len(arr):
        markup.row(*arr)
    return markup

# inline-кнопки для выбора предметов в меню олимпиад (все сделано для того, чтобы нажимаю на готово наше инлайн меню перезагружалось)
async def create_subjects_markup_for_olympiads_menu(chat_id, subject_names):
    markup = types.InlineKeyboardMarkup()
    subjects = subject_names.copy()
    cnt = 0
    arr = []
    for subj in subjects:
        if subj == "Генетика":
            continue
        arr.append(types.InlineKeyboardButton(text=f"{'✅' if await db.get_sub(chat_id, subj) else ''} {subj}", callback_data=f"{subj}_for_olympiad_menu"))
        cnt += 1
        if cnt == 3:
            markup.row(*arr)
            arr = []
            cnt = 0
    arr.append(types.InlineKeyboardButton(text="Готовo", callback_data='done_from_olympiad_menu')) # (последняя о - английская)
    if len(arr):
        markup.row(*arr)
    return markup

# inline-кнопки для выбора класса
async def create_class_markup_for_olympiads_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    classes = ["8", "9", "10", "11", "Не школьник", "Учитель"]
    for cl in classes:
        markup.add(types.InlineKeyboardButton(text=cl, callback_data=f"{cl}_for_olympiad_menu"))
    return markup


async def create_mailing_menu(chat_id):
    markup = types.InlineKeyboardMarkup()
    mailing = ["Олимпиады", "Хакатоны", "Ивенты по программированию", "Готово"]
    markup.add(types.InlineKeyboardButton(text=f"{'✅' if await db.get_mailing_olympiads_state(chat_id) else '❌'} Олимпиады", callback_data=mailing[0]))
    markup.add(types.InlineKeyboardButton(text=f"{'✅' if await db.get_mailing_hackathons_state(chat_id) else '❌'} Хакатоны", callback_data=mailing[1]))
    markup.add(types.InlineKeyboardButton(text=f"{'✅' if await db.get_mailing_status_of_programming(chat_id) else '❌'} Ивенты по программированию", callback_data=mailing[2]))
    markup.add(types.InlineKeyboardButton(text="➡️ Готово", callback_data=mailing[3]))

    return markup


async def create_olimpiads_markup(chat_id, db):
    user_subjects = await db.get_users_subjects_names(chat_id)
    markup = types.InlineKeyboardMarkup()
    for subject in user_subjects:
        markup.add(types.InlineKeyboardButton(text=subject, callback_data="list_" + subject))
    
    return markup

# inline-кнопки для выбора предметов
async def create_olimpiads_markup_for_teachers():
    subject_names = await db.get_subject_names() # список названий всех предметов
    subject_names.sort()
    markup = types.InlineKeyboardMarkup()
    cnt = 0
    arr = []
    for subj in subject_names:
        if subj == "Генетика":
            continue
        arr.append(types.InlineKeyboardButton(text=subj, callback_data="list_" + subj))
        cnt += 1
        if cnt == 3:
            markup.row(*arr)
            arr = []
            cnt = 0
    if len(arr):
        markup.row(*arr)
    return markup

async def create_cancel_markup():
    markup = types.InlineKeyboardMarkup()
    cancel = types.InlineKeyboardButton('❌ Отмена', callback_data='cancel')
    markup.add(cancel)
    return markup

async def create_remind_markup(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    days = ["1", "3", "7", "14"]
    for day in days:
        text = ""
        if await db.get_remind_day(chat_id, day):
            text += "✅ "
        text += day
        markup.add(types.InlineKeyboardButton(text, callback_data="day_" + day))
    return markup

async def create_remind_markup_for_registration(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    days = ["1", "3", "7", "14"]
    for day in days:
        text = ""
        if await db.get_remind_day(chat_id, day):
            text += "✅ "
        text += day
        markup.add(types.InlineKeyboardButton(text, callback_data="registration_day_" + day))
    markup.add(types.InlineKeyboardButton("Готово", callback_data="callback_end_registration"))
    return markup