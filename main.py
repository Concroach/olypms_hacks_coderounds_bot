import os, csv, json
import numpy as np
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import atexit
import time
from datetime import datetime, timedelta, date
from os.path import join, dirname
from dotenv import load_dotenv
from multiprocessing import Process

import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.utils.exceptions import BotBlocked

from db import Database
from markup import * 
from middlewares import ThrottlingMiddleware, rate_limit
from logic import list_of_olympiads, list_of_camps, list_of_hacks, show_subject_olympiads
from logic import mailing, send_logs
from logic import codeforces_rounds, leetcode_rounds, codechef_rounds
from analytics import send_analytics

# список с названиями кнопок
buttons_list = ["Олимпиады", "Хакатоны", "Программирование", "Контесты", "Настройки", "Тех поддержка", 
                    "Вернуться в главное меню", "Вернуться в меню 'Программирование'",
                    "Включить рассылку олимпиад", "Выключить рассылку олимпиад",
                    "Включить рассылку хакатонов", "Выключить рассылку хакатонов", 
                    "Выключить рассылку", "Включить рассылку", 'Список хакатонов', 
                    'Список олимпиад', 'Список лагерей', 'Codeforces', 'CodeChef', 'LeetCode', 
                    'Международные олимпиады', 'Изменить класс', 'Изменить предметы', "Напоминать 🔔"]


# класс для запуска расслыки
scheduler = AsyncIOScheduler()

# получение данных из env.env
def get_from_env(key):
    dotenv_path = join(dirname(__file__), 'env.env')
    load_dotenv(dotenv_path)
    return os.environ.get(key)


logger.add("debug.log", format="{time} {level} {message}", filter=lambda record: record["level"].name == "DEBUG")
logger.add("info.log", format="{time} {level} {message}", filter=lambda record: record["level"].name == "INFO")
logger.add("error.log", format="{time} {level} {message}", filter=lambda record: record["level"].name == "ERROR")

TOKEN_API = 'XXXX'
storage = MemoryStorage()
bot = Bot(TOKEN_API)  # бот
dp = Dispatcher(bot=bot, storage=storage)
db = Database()  # экземпляр класса Database() для работы с базой данных
logger.info("Begin")

asyncio.get_event_loop().run_until_complete(db.async_init())

# берём сохранённые данные
with open("analytics_data.json", 'r') as openfile:
    json_objects = json.load(openfile)
count_new_users = json_objects["count_new_users"]
prev_count_users = json_objects["prev_count_users"]
total_messages = json_objects["total_messages"]
str_prev_date = json_objects["prev_date"]
year, month, day = map(int, str_prev_date.split('-'))
prev_date = date(year, month, day)
activity_with_str_keys = json_objects["activity"]
activity = {}
for i in range(24):
    activity[i] = activity_with_str_keys[str(i)]

subject_names = asyncio.get_event_loop().run_until_complete(db.get_subject_names())  # список названий всех предметов
subject_names.sort()
list_subject_names = []
for elem in subject_names:
    list_subject_names.append("list_" + elem)


subject_names_for_olympiad_menu = []
for elem in subject_names:
    subject_names_for_olympiad_menu.append(elem + "_for_olympiad_menu")
    

# функция вызывается в момент завершения работы программы.
# сохраняем данные для аналитики
# @atexit.register
async def goodbye():
    global count_new_users, prev_count_users, total_messages, prev_date, activity
    # сохранение данных
    # формируем словарь data
    data = {}
    data["count_new_users"] = count_new_users
    data["prev_count_users"] = prev_count_users
    data["total_messages"] = total_messages
    data["prev_date"] = prev_date
    data["activity"] = activity

    # запись в json
    with open("analytics_data.json", "w") as outfile:
        json.dump(data, outfile, default=str)


# аналитика сообщений (всех нажатий)
def analytics_messages(func: callable):
    async def analytics_wrapper(message):
        global prev_date, total_messages, activity

        # проверка - если начался новый день, мы сохраняем данные за прошлый день
        # и устанавливаем новую дату
        cur_date = date.today()
        if cur_date != prev_date:
            logger.info("saving data...")
            await save_analytics(prev_date)
            prev_date = cur_date

        # сама логика: увеличиваем счётчик количества сообщений, заполняем активность
        total_messages += 1
        # +3 часа, чтобы время было московское
        current_hour = (datetime.now().hour + 3) % 24 # datetime.now().minute
        activity[current_hour] += 1


        return await func(message)
    
    return analytics_wrapper


# аналитика callback`ов
def analytics_callback(func: callable):
    async def analytics_wrapper(call):
        global prev_date, total_messages, activity
        # та же проверка на новый день
        cur_date = date.today()  # datetime.now().minute
        if cur_date != prev_date:
            logger.info("saving data...")
            await save_analytics(prev_date)
            prev_date = cur_date

        # заполняем активность
        total_messages += 1
        # +3 часа, чтобы время было московское
        current_hour = (datetime.now().hour + 3) % 24 # datetime.now().minute
        activity[current_hour] += 1

        return await func(call)
    
    return analytics_wrapper


def analytics_message_state(func: callable):
    async def analytics_wrapper(message, state):
        global prev_date, total_messages, activity
        # та же проверка на новый день
        cur_date = date.today()  # datetime.now().minute
        if cur_date != prev_date:
            logger.info("saving data...")
            await save_analytics(prev_date)
            prev_date = cur_date


        # заполняем активность
        total_messages += 1
        # +3 часа, чтобы время было московское
        current_hour = (datetime.now().hour + 3) % 24 # datetime.now().minute
        activity[current_hour] += 1

        return await func(message, state)
    
    return analytics_wrapper


def analytics_callback_state(func: callable):
    async def analytics_wrapper(call, state):
        global prev_date, total_messages, activity
        # та же проверка на новый день
        cur_date = date.today()
        if cur_date != prev_date:
            logger.info("saving data...")
            await save_analytics(prev_date)
            prev_date = cur_date


        # заполняем активность
        total_messages += 1
        # +3 часа, чтобы время было московское
        current_hour = (datetime.now().hour + 3) % 24 # datetime.now().minute
        activity[current_hour] += 1

        return await func(call, state)
    
    return analytics_wrapper


async def save_analytics(today_date):
    global count_new_users, prev_count_users, total_messages, activity
    # шапка
    fieldnames = ['date', 'count_users', 'new_users', 'deleted_users', "total_messages"]
    for i in range(24):
        fieldnames.append(f"activity_{i}")
    # запись данных в csv файл
    with open("analytics.csv", "a", newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        # writer.writeheader() # запись заголока
        # формируем строку для записи
        row = {}
        row["date"] = today_date
        all_users = await db.get_all_users()
        row["count_users"] = len(all_users)
        row['new_users'] = count_new_users
        # кол-во отписавшихся - это кол-во пользователей в бд за предыдущий день + новые пользователи - сколько сейчас пользователй в бд 
        row["deleted_users"] = prev_count_users + count_new_users - len(all_users)
        prev_count_users = len(all_users)
        row["total_messages"] = total_messages
        for i in range(24):
            row[f"activity_{i}"] = activity[i]
        writer.writerow(row)

    # обнуляем данные для нового дня
    count_new_users = 0
    total_messages = 0
    for i in range(24):
        activity[i] = 0


# обработчик команды '/start'
@dp.message_handler(commands=['start'])
@rate_limit(10, 'start')
@analytics_messages
async def start(message):
    chat_id = message.chat.id
    username = f'@{message.chat.username}'
    # если пользователя нет в бд - он новый, регистрируем его. Иначе выводим сообщение о попытке повторной регистрации
    res = await db.user_exists(chat_id)
    if res:
        await bot.send_message(chat_id=message.chat.id, 
                         text="С возвращением!\nВы уже зарегистрированы.", reply_markup=await create_main_menu())
    else:
        # новый пользователь
        global count_new_users
        count_new_users += 1
        await bot.send_message(message.chat.id, text="Привет, пройди небольшую регистрацию")
        await db.add_user_id(chat_id, username)
        markup = await create_class_markup(chat_id)
        await bot.send_message(chat_id=message.chat.id, text="Выбери класс", reply_markup=markup)


# обработчик выбора класса
@dp.callback_query_handler(lambda call: call.data in ["8", "9", "10", "11", "Не школьник", "Учитель"])
@analytics_callback
async def class_callback(call):
    cl = call.data
    chat_id = call.from_user.id
    user_status = await db.get_user_registration_status(chat_id)
    if user_status:
        if cl != "Учитель":
            await db.add_class(chat_id, cl)
            if cl == "Не школьник":
                await db.add_status_to_teacher(chat_id, False)
                await db.update_user_mailing_olympiads(chat_id, False)
                await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                    text=f'''✅ *Изменения успешно внесены!*\nВыбранный класс: {await db.get_class_for_registration_is_done(chat_id)}''', parse_mode='Markdown')
            else:
                if await db.check_flag_teachers_searching(chat_id):
                    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                        text=f'''✅ *Изменения успешно внесены!*\nВыбранный класс: {await db.get_class_for_registration_is_done(chat_id)}\nВыбранные предметы: {await db.get_subs_for_registration_is_done(chat_id)}''', reply_markup=None, parse_mode='Markdown')
                    await db.change_flag_teachers_searching(chat_id, False)
                else:
                    await db.add_status_to_teacher(chat_id, False)
                    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                        text=f'''✅ *Изменения успешно внесены!*\nВыбранный класс: {await db.get_class_for_registration_is_done(chat_id)}\nВыбранные предметы: {await db.get_subs_for_registration_is_done(chat_id)}''', reply_markup=None, parse_mode='Markdown')
        else:
            await db.del_user_class(chat_id)
            await db.add_status_to_teacher(chat_id, True)
            markup = await create_class_markup_for_teacher(chat_id)
            await db.change_flag_teachers_searching(chat_id, True)
            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Выберите класс, для которого Вы хотите узнавать олимпиады", reply_markup=markup, parse_mode='Markdown')
    else:
        if cl != "Учитель":
            if cl == "Не школьник":
                await db.add_class(chat_id, cl)
                await db.update_user_mailing_olympiads(chat_id, False)
                markup = await create_mailing_menu(chat_id)
                await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Выберите по каким разделам желаете получать рассылку:", reply_markup=markup)
            else:
                if db.check_teacher_status(chat_id):
                    await db.add_class(chat_id, cl)
                    markup = await create_subjects_markup(chat_id, subject_names)
                    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                    text="Выберите предметы *(максимальное количество 5)*, по которым вы хотите получать рассылку", reply_markup=markup, parse_mode='Markdown')
                else:
                    markup = await create_subjects_markup(chat_id, subject_names)
                    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                                    text="Выбери предметы *(максимальное количество 5)*", reply_markup=markup, parse_mode='Markdown')
        else:
            await db.add_status_to_teacher(chat_id, True)
            markup = await create_class_markup_for_teacher(chat_id)
            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Выберите класс, для которого Вы хотите узнавать олимпиады", reply_markup=markup, parse_mode='Markdown')


# обработчик выбора предметов
@dp.callback_query_handler(lambda call: call.data in subject_names)
@analytics_callback
async def subjects_callback(call):
    subj = call.data
    chat_id = call.from_user.id
    subj_id = await db.get_subjects_id(subj)
    flag = await db.add_del_sub(chat_id, subj_id)  # True - есть изменения, False - нет
    markup = await create_subjects_markup(chat_id, subject_names)
    if flag is True:
        await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    else:
        await bot.answer_callback_query(callback_query_id=call.id, text='Максимальное кол-во предметов: 5')


@dp.callback_query_handler(lambda call: call.data in subject_names_for_olympiad_menu)
@analytics_callback
async def subjects_callback_for_olympiad_menu(call):
    subj = call.data.split('_')[0]
    chat_id = call.from_user.id
    subj_id = await db.get_subjects_id(subj)
    flag = await db.add_del_sub(chat_id, subj_id)  # True - есть изменения, False - нет
    markup = await create_subjects_markup_for_olympiads_menu(chat_id, subject_names)
    if flag is True:
        await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    else:
        await bot.answer_callback_query(callback_query_id=call.id, text='Максимальное кол-во предметов: 5')


@dp.callback_query_handler(lambda call: call.data.startswith("day_"))
@analytics_callback
async def remind_callback(call):
    day = call.data.split('_')[1]
    chat_id = call.from_user.id
    user_days = await db.get_user_remind_days(chat_id)
    str_days = user_days[0][0]
    list_days = str_days.split()
    if day not in list_days:
        list_days.append(day)
    else:
        list_days.remove(day)
    new_str = ' '.join(list_days)
    await db.update_user_remind_days(chat_id, new_str)
    markup = await create_remind_markup(chat_id)
    await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)


@dp.callback_query_handler(lambda call: call.data.startswith("registration_day_"))
@analytics_callback
async def remind_callback(call):
    day = call.data.split('_')[-1]
    chat_id = call.from_user.id
    user_days = await db.get_user_remind_days(chat_id)
    str_days = user_days[0][0]
    list_days = str_days.split()
    if day not in list_days:
        list_days.append(day)
    else:
        list_days.remove(day)
    new_str = ' '.join(list_days)
    print(day, user_days, str_days, list_days, new_str) 
    await db.update_user_remind_days(chat_id, new_str)
    markup = await create_remind_markup_for_registration(chat_id)
    await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

# обработчик выбора предмета для показа списков олимпиад
@dp.callback_query_handler(lambda call: call.data in list_subject_names)
@analytics_callback
async def subjects_callback_for_output_list_of_olympiads(call):
    subj = call.data
    chat_id = call.from_user.id
    await bot.edit_message_text(chat_id=call.message.chat.id, 
                                message_id=call.message.message_id,
                                text=f"Выбранный предмет: {subj[5:]}")
    await show_subject_olympiads(chat_id, bot, db, subj[5:])


# окончание регистрации
@dp.callback_query_handler(lambda call: call.data == 'done')
@analytics_callback
async def registration_is_done_callback(call):
    chat_id = call.message.chat.id
     
    user_subjects = await db.get_subs_for_registration_is_done(chat_id)
    user_status = await db.get_user_registration_status(chat_id)
    user_class = await db.get_class_for_registration_is_done(chat_id)
    if not user_status:
        markup = await create_mailing_menu(chat_id)
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Выберите по каким разделам желаете получать рассылку:", reply_markup=markup)
    else:
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                        text=f'✅ *Изменения успешно внесены!*\n' + \
                            f'Выбранный класс: {user_class}\n' + \
                            f'Выбранные предметы: {user_subjects}', parse_mode='Markdown')
        

@dp.callback_query_handler(lambda call: call.data == 'callback_end_registration')
@analytics_callback
async def select_remind_end_callback(call):
    chat_id = call.message.chat.id
    user_subjects = await db.get_subs_for_registration_is_done(chat_id)
    main_menu = await create_main_menu()
    user_class = await db.get_class_for_registration_is_done(chat_id)
    current_class = await db.get_class(chat_id, "Не школьник")
    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                        text=f'*Поздравляем, регистрация закончена.*\n' + \
                            f'Выбранный класс: {user_class}\n' + \
                            f'Выбранные предметы: {user_subjects}',
                        parse_mode='Markdown')
    if await db.check_teacher_status(chat_id):
        await bot.send_message(chat_id=call.message.chat.id, 
                        text='Теперь Вы сможете следить за актуальными олимпиадами и хакатонами. Успехов Вам и вашим ученикам!',
                        reply_markup=main_menu)
    else:
        if current_class: 
            await bot.send_message(chat_id=call.message.chat.id, 
                text='Теперь ты можешь следить за актуальными хакатонами и мероприятиями по программированию. Успехов!',
                reply_markup=main_menu)   
        else:
            await bot.send_message(chat_id=call.message.chat.id, 
                            text='Теперь ты можешь следить за актуальными олимпиадами и хакатонами. Успехов!',
                            reply_markup=main_menu)
    await db.end_user_registration(call.message.chat.id)
        
        
@dp.callback_query_handler(lambda call: call.data == 'done_from_olympiad_menu')
@analytics_callback
async def registration_is_done_from_olympiad_menu_callback(call):
    chat_id = call.message.chat.id
     
    user_subjects = await db.get_subs_for_registration_is_done(chat_id)
    user_class = await db.get_class_for_registration_is_done(chat_id)
    await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                text=f'✅ *Изменения успешно внесены!*\n' + \
                    f'Выбранный класс: {user_class}\n' + \
                    f'Выбранные предметы: {user_subjects}', parse_mode='Markdown')
    await list_of_olympiads(chat_id, bot, db)

    
@dp.callback_query_handler(lambda call: call.data in ["Олимпиады", "Хакатоны", "Ивенты по программированию", "Готово"])
@analytics_callback
async def mailing_callback(call):
    mailing = call.data
    chat_id = call.from_user.id
    message_id = call.message.message_id
    current_class = await db.get_class(chat_id, "Не школьник")
    if mailing == "Олимпиады":
        if current_class:
            await bot.answer_callback_query(callback_query_id=call.id, text='Вы не можете изменить статус рассылки олимпиад')
        else:
            current_mailing_status = await db.get_mailing_olympiads_state(chat_id)
            if current_mailing_status:
                await db.update_user_mailing_olympiads(chat_id, False)
            else:
                await db.update_user_mailing_olympiads(chat_id, True)
            
    if mailing == "Хакатоны":
        current_mailing_status = await db.get_mailing_hackathons_state(chat_id)
        if current_mailing_status:
            await db.update_user_mailing_hackathons(chat_id, False)
        else:
            await db.update_user_mailing_hackathons(chat_id, True)
            
    if mailing == "Ивенты по программированию":
        current_mailing_status = await db.get_mailing_status_of_programming(chat_id)
        if current_mailing_status:
            await db.update_user_mailing_programming(chat_id, False)
        else:
            await db.update_user_mailing_programming(chat_id, True)
            
    if mailing == "Готово":
        if await db.get_mailing_olympiads_state(chat_id):
            markup = await create_remind_markup_for_registration(chat_id)
            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Выберите, за сколько дней хотите получать напоминания об олимпиадах.\nЕсли не хотите получать напоминания, сразу нажмите 'Готово':", reply_markup=markup)
        else:
            user_subjects = await db.get_subs_for_registration_is_done(chat_id)
            main_menu = await create_main_menu()
            user_class = await db.get_class_for_registration_is_done(chat_id)
            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                text=f'*Поздравляем, регистрация закончена.*\n' + \
                                    f'Выбранный класс: {user_class}\n' + \
                                    f'Выбранные предметы: {user_subjects}',
                                parse_mode='Markdown')
            if await db.check_teacher_status(chat_id):
                await bot.send_message(chat_id=call.message.chat.id, 
                                text='Теперь Вы сможете следить за актуальными олимпиадами и хакатонами. Успехов Вам и вашим ученикам!',
                                reply_markup=main_menu)
            else:
                if current_class: 
                    await bot.send_message(chat_id=call.message.chat.id, 
                        text='Теперь ты можешь следить за актуальными хакатонами и мероприятиями по программированию. Успехов!',
                        reply_markup=main_menu)   
                else:
                    await bot.send_message(chat_id=call.message.chat.id, 
                                    text='Теперь ты можешь следить за актуальными олимпиадами и хакатонами. Успехов!',
                                    reply_markup=main_menu)
            await db.end_user_registration(call.message.chat.id)
    else:
        markup = await create_mailing_menu(chat_id)
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Выберите по каким разделам желаете получать рассылку:", reply_markup=markup)


class SupportStates(StatesGroup):
    deal = State()
    mail_choose_subjects = State()
    mail = State()


@dp.message_handler(regexp='Тех поддержка', content_types=['text'])
@rate_limit(5, 'text6')
@analytics_messages
async def support_handler(message: types.Message):
    result = await db.check_ban(message.chat.id)
    if not len(result):
        await SupportStates.deal.set()
        await message.reply("💬 Введи своё сообщение, при необходимости прикрепи фото или видео", reply_markup=await create_cancel_markup())
    else:
        new_menu = await create_main_menu()
        await message.reply("Вы больше не можете обращаться в техподдержку", reply_markup=new_menu)


@dp.callback_query_handler(lambda call: call.data in ["cancel"], state=SupportStates.deal)
@analytics_callback_state
async def cancel_button_in_ts(call, state):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text='☑️ Обращение отменено')
    await state.finish()


# Обработчик ввода сообщения
@dp.message_handler(state=SupportStates.deal, content_types=types.ContentTypes.ANY)
@analytics_message_state
async def process_support_message(message: types.Message, state: FSMContext):
    if message.text in buttons_list:
        new_menu = await create_main_menu()
        await message.answer("😉 Понимаем, случайно нажали, можете продолжить", reply_markup=new_menu)
    else:
        if message.content_type == 'photo':
            photo_id = message.photo[-1].file_id
            photo = await bot.get_file(photo_id)
            text = f'Сообщение пользователя:\n{message.caption}\nОтветить: `/answer_ts {message.chat.id}`\nЗабанить: `/ban {message.chat.id}` '
            await bot.send_photo(chat_id=-1001928271501, photo=photo.file_id, caption=text, parse_mode="MARKDOWN")
        elif message.content_type == 'video':
            video_id = message.video.file_id
            video = await bot.get_file(video_id)
            text = f'Сообщение пользователя:\n{message.caption}\nОтветить: `/answer_ts {message.chat.id}`\nЗабанить: `/ban {message.chat.id}` '
            await bot.send_video(chat_id=-1001928271501, video=video.file_id, caption=text, parse_mode="MARKDOWN")
        else:
            text = f'Сообщение пользователя:\n{message.text}\nОтветить: `/answer_ts {message.chat.id}`\nЗабанить: `/ban {message.chat.id}` '
            await bot.send_message(chat_id=-1001928271501, text=text, parse_mode="MARKDOWN")
        new_menu = await create_main_menu()
        await message.answer("✉️✅ Сообщение отправлено оператору, ожидайте", reply_markup=new_menu)
    await state.finish()


# обработчик кнопок меню
@dp.message_handler(regexp='Олимпиады|Хакатоны|Программирование|Контесты|Настройки|Вернуться в главное меню|Вернуться в меню \'Программирование\'|Включить рассылку олимпиад|Выключить рассылку олимпиад|Включить рассылку хакатонов|Выключить рассылку хакатонов|Включить рассылку|Выключить рассылку', content_types=['text'])
@analytics_messages
async def change_menu(message):
    if message.text in buttons_list:
        new_menu = None  # новое меню
        if message.text == "Олимпиады":
            user_class = await db.get_class_for_registration_is_done(message.chat.id)
            if user_class == 'Не школьник':
                await bot.send_message(chat_id=message.chat.id, text="❌ Раздел олимпиад доступен только для школьников.\nПерейдите в \"Настройки\" ➡️ \"Изменить класс\"", parse_mode='Markdown')
            else:
                new_menu = await create_olympiads_menu(message.chat.id)
        elif message.text == "Выключить рассылку олимпиад":
            await db.update_user_mailing_olympiads(message.chat.id, False)
            new_menu = await create_olympiads_menu(message.chat.id)
        elif message.text == "Включить рассылку олимпиад":
            await db.update_user_mailing_olympiads(message.chat.id, True)
            new_menu = await create_olympiads_menu(message.chat.id)
        elif message.text == "Хакатоны":
            new_menu = await create_hackathons_menu(message.chat.id)
        elif message.text == "Программирование":
            new_menu = await create_prog_menu(message.chat.id)
        elif message.text == "Выключить рассылку":
            await db.update_user_mailing_programming(message.chat.id, False)
            new_menu = await create_prog_menu(message.chat.id)
        elif message.text == "Включить рассылку":
            await db.update_user_mailing_programming(message.chat.id, True)
            new_menu = await create_prog_menu(message.chat.id)
        elif message.text == "Контесты":
            new_menu = await create_training_menu(message.chat.id)
        elif message.text == "Выключить рассылку хакатонов":
            await db.update_user_mailing_hackathons(message.chat.id, False)
            new_menu = await create_hackathons_menu(message.chat.id)
        elif message.text == "Включить рассылку хакатонов":
            await db.update_user_mailing_hackathons(message.chat.id, True)
            new_menu = await create_hackathons_menu(message.chat.id)
        elif message.text == "Настройки":
            new_menu = await create_settings_menu()
        elif message.text == "Вернуться в меню 'Программирование'":
            new_menu = await create_prog_menu(message.chat.id)
        elif message.text == "Вернуться в главное меню":
            new_menu = await create_main_menu()
        user_class = await db.get_class_for_registration_is_done(message.chat.id)
        if user_class != 'Не школьник':
            await bot.send_message(chat_id=message.chat.id, text=menu_answers[message.text], reply_markup=new_menu)
            if message.text == "Олимпиады":
                await list_of_olympiads(message.chat.id, bot, db)
        else:
            if message.text != 'Олимпиады':
                await bot.send_message(chat_id=message.chat.id, text=menu_answers[message.text], reply_markup=new_menu)    


@dp.message_handler(regexp='Список хакатонов', content_types=['text'])
@rate_limit(10, 'text2')
@analytics_messages
async def list_h(message):
    if message.text == "Список хакатонов":
        markup = await create_hackathons_menu(message.chat.id)
        await bot.send_message(chat_id=message.chat.id, text="Список хакатонов", reply_markup=markup)
        await list_of_hacks(message.chat.id, bot, db)


@dp.message_handler(regexp='Список лагерей', content_types=['text'])
@rate_limit(10, 'Список лагерей')
@analytics_messages
async def list_ol(message):
    if message.text == "Список лагерей":
        markup = await create_olympiads_menu(message.chat.id)
        await bot.send_message(chat_id=message.chat.id, text="Список лагерей", reply_markup=markup)
        await list_of_camps(message.chat.id, bot, db)


@dp.message_handler(regexp='Codeforces', content_types=['text'])
@rate_limit(4, 'Codeforces')
@analytics_messages
async def list_codeforces(message):
    if message.text == "Codeforces":
        await codeforces_rounds(message.chat.id, bot, db)


@dp.message_handler(regexp='CodeChef', content_types=['text'])
@rate_limit(4, 'CodeChef')
@analytics_messages
async def list_codeforces(message):
    if message.text == "CodeChef":
        markup = await create_prog_menu(message.chat.id)
        await codechef_rounds(message.chat.id, bot, db)


@dp.message_handler(regexp='LeetCode', content_types=['text'])
@rate_limit(4, 'LeetCode')
@analytics_messages
async def list_leetcode(message):
    if message.text == "LeetCode":
        await leetcode_rounds(message.chat.id, bot, db)


@dp.message_handler(regexp='Международные олимпи', content_types=['text'])
@rate_limit(4, 'text101')
@analytics_messages
async def list_international_ol(message):
    if message.text == "Международные олимпиaды":
        text = '*Международные олимпиады*\n*1. Advent of Code*\nЭто мероприятие проходит с 1 по 25 декабря\nОно состоит из 25 раундов, каждый день на сайте будет появляться задание, кто больше решил, тот и победил\n[Ссылка на ресурс](https://hpecodewars.org/)\n\n*2. ICFP Programming Contest*\nРегистрация доступна до сентября. Мероприятие пройдет с 4 по 9 сентрября 2023\n[Ссылка на ресурс](https://web.cvent.com/event/db55e0d8-c55e-429d-8c04-01bd48913fdc/summary)\n\n*3. Microsoft Imagine Cup Junior 2024*\nДля детей от 13 до 18 лет\nРегистрация 12 января - 14 мая 2024\n[Ссылка на ресурс](https://imaginecup.microsoft.com/ru-ru/junior)\n\n*4. Microsoft - Imagine Cup 2024*\nРегистрация доступна круглый год. Мероприятие проходит летом.\n[Ссылка на ресурс](https://imaginecup.microsoft.com/category/register/27)\n\n*5. CodeWars 2024*\nМероприятие пройдет в субботу 2 марта 2024\n[Ссылка на ресурс](https://hpecodewars.org/)'
        await bot.send_message(chat_id=message.chat.id, text=text, parse_mode='MARKDOWN', disable_web_page_preview=True)
        
        
@dp.message_handler(regexp='Изменить класс', content_types=['text'])
@rate_limit(5, 'text4')
@analytics_messages
async def change_cl(message):
    if message.text == "Изменить класс":
        markup = await create_class_markup(message.chat.id)
        await bot.send_message(chat_id=message.chat.id, text="Выберите класс", reply_markup=markup)
        
        
@dp.message_handler(regexp='Изменить предметы', content_types=['text'])
@rate_limit(5, 'text5')
@analytics_messages
async def change_subs(message):    
    if message.text == "Изменить предметы":
        user_class = await db.get_class_for_registration_is_done(message.chat.id)
        if user_class == 'Не школьник':
            await bot.send_message(chat_id=message.chat.id, text="❌ Выбор предметов доступен только для школьников.\nПерейдите в \"Изменить класс\"", parse_mode='Markdown')
        else:
            markup = await create_subjects_markup(message.chat.id, subject_names)
            await bot.send_message(chat_id=message.chat.id, text="Выбери предметы, *(максимальное количество 5)*", reply_markup=markup, parse_mode='Markdown')


# первая e - английская
@dp.message_handler(regexp='Измeнить предметы', content_types=['text'])
@rate_limit(5, 'text5')
@analytics_messages
async def change_subs_for_teacher_in_olympiad_menu(message):    
    if message.text == "Измeнить предметы":
        markup = await create_subjects_markup_for_olympiads_menu(message.chat.id, subject_names)
        await bot.send_message(chat_id=message.chat.id, text="Выбери предметы, *(максимальное количество 5)*", reply_markup=markup, parse_mode='Markdown')
   
            
# первая e - английская
@dp.message_handler(regexp='Измeнить класс', content_types=['text'])
@rate_limit(5, 'text5')
@analytics_messages
async def change_class(message):    
    if message.text == "Измeнить класс":
        await db.change_flag_teachers_searching(message.chat.id, True)
        markup = await create_class_markup_for_teacher(message.chat.id)
        await bot.send_message(chat_id=message.chat.id, text="Выберите класс", reply_markup=markup, parse_mode='Markdown')


@dp.message_handler(regexp='Напоминать 🔔', content_types=['text'])
@rate_limit(5, 'text_remind')
@analytics_messages
async def change_cl(message):
    if message.text == "Напоминать 🔔":
        if await db.get_mailing_olympiads_state(message.chat.id):
            markup = await create_remind_markup(message.chat.id)
            await bot.send_message(chat_id=message.chat.id, text="За сколько дней хотите получать напоминание об олимпиаде?", reply_markup=markup)
        else:
            await bot.send_message(chat_id=message.chat.id, text="Включите рассылку олимпиад, чтобы получать напоминания")

"""Команды в чате тп"""
@dp.message_handler(commands=['help'])
async def send_help_command(message):
        await message.reply("""Команды:\n- /mail - рассылка сообщений по чатам.(all - все предметы, not_reg - только кто не закончил регистрацию. в остальных случаях - предметы через запятую)\n- /answer_ts - ответ на обращение пользователя.\nСинтаксис: команда, user_id и сам ответ (пример: /answer_ts 123456 напишите на почту bot@bot) \n- /ban - ограничить пользователю отправку сообщений.\nСинтаксис: команда, user_id и причина бана (пример: /ban 123456 отправлял сообщения не по теме)\n- /unban - разрешить пользователю отправку сообщений.\nСинтаксис: команда и user_id через пробел (пример: /unban 123456)\n- /get_analytics - получение pdf-файла с аналитикой\n- /get_logs - отправка логов\n- /get_now_analytics - текущие значения переменных для аналитики\n- /get_subjects_count - сколько человек выбрали предмет\n- /save_users - копия user в базе данных""")


@dp.message_handler(commands=['mail'])
async def func_begin_mail(message):
    if message.chat.id == -1001928271501:
        await SupportStates.mail_choose_subjects.set()
        await message.reply("Введите предметы через запятую(если надо все, введите all. если только тем, кто не закончил регистрацию - not_reg)")


@dp.message_handler(commands=['answer_ts'])
async def answer_from_ts(message):
    if message.chat.id == -1001928271501:
        command, chat_id, *text = message.text.split()
        text = ' '.join(text)
        msg = f'🧑‍💻 Ответ на ваше обращение:\n{text}\n❤️Благодарим за обращение!'
        await bot.send_message(chat_id=chat_id, text=msg)


@dp.message_handler(commands=['ban'])
async def ban_user_in_ts(message):
    if message.chat.id == -1001928271501:
        command, chat_id, *text = message.text.split()
        text = ' '.join(text)
        await db.ban_user(chat_id, text)
        msg = "Вы больше не можете обращаться в техподдержку"
        await bot.send_message(chat_id=chat_id, text=msg)


@dp.message_handler(commands=['unban'])
async def unban_user_in_ts(message):
    if message.chat.id == -1001928271501:
        command, chat_id = message.text.split()
        await db.unban_user(chat_id)
        msg = "Вы снова можете обращаться в техподдержку"
        await bot.send_message(chat_id=chat_id, text=msg)


@dp.message_handler(commands=['get_analytics'])
async def func_analytics(message):
    if message.chat.id == -1001928271501:
        await send_analytics(bot, db)


@dp.message_handler(commands=['get_now_analytics'])
async def func_now_analytic(message):
    if message.chat.id == -1001928271501:
        global count_new_users, total_messages, activity
        message = "*Текущие данные*\n"
        message += f"Количество пользователей в бд: {len(await db.get_all_users())}\n"
        message += f"Завершило регистрацию: {len(await db.get_users_ended_registration())}\n"
        message += f"Не завершило регистрацию: {len(await db.get_users_not_ended_registration())}\n"
        message += f"Количество новых пользователей: {count_new_users}\n"
        message += f"Количество сообщений: {total_messages}\n"
        message += "Статистика сообщений по часам:\n"
        for i in range(24):
            message += f"{i}: {activity[i]}\n"
        await bot.send_message(chat_id=-1001928271501, text=message, parse_mode="MARKDOWN")


@dp.message_handler(commands=['get_logs'])
async def func_logs(message):
    if message.chat.id == -1001928271501:
        await send_logs(bot)


@dp.message_handler(commands=['get_subjects_count'])
async def admin_state(message):
    if message.chat.id == -1001928271501:
        d_subjects = {}
        all_subjects_names = await db.get_subject_names()
        for elem in all_subjects_names:
            if elem == "Генетика":
                continue
            d_subjects[elem] = 0
        
        all_users = await db.get_all_users()
        for user in all_users:
            user_subs = await db.get_users_subjects_names(user[0])
            for sub in user_subs:
                d_subjects[sub] += 1
        keys = list(d_subjects.keys())
        values = list(d_subjects.values())
        tups = []
        for i in range(len(keys)):
            tups.append((keys[i], values[i]))
        tups.sort(key=lambda x: x[1], reverse=True)
        message = ''
        for tup in tups:
            message += f"{tup[0]}: {tup[1]}\n"
        await bot.send_message(chat_id=-1001928271501, text=message, parse_mode="MARKDOWN")


@dp.message_handler(state=SupportStates.mail_choose_subjects, content_types=types.ContentTypes.ANY)
async def process_subjects(message: types.Message, state: FSMContext):
    if message.chat.id == -1001928271501:
        await state.update_data({"subjects": message.text})
        await SupportStates.mail.set()
        await message.reply("Введите сообщение для рассылки")


@dp.message_handler(state=SupportStates.mail, content_types=types.ContentTypes.ANY)
async def process_support_message(message: types.Message, state: FSMContext):
    if message.chat.id == -1001928271501:
        data = await state.get_data()
        subjects = data.get("subjects").split(',')
        for i in range(len(subjects)):
            subjects[i] = subjects[i].strip().capitalize()
        file = open('log_mail.txt', 'w')
        cnt = 0
        if message.content_type == 'photo':
            photo_id = message.photo[-1].file_id
            photo = await bot.get_file(photo_id)
            for i in await db.get_all_users():
                for j in i:
                    if subjects[0].lower() == "all":
                        try:
                            await bot.send_photo(chat_id=j, photo=photo.file_id, caption=message.caption, parse_mode="MARKDOWN")
                            file.write(f'sent photo to user with id {j}\n')
                            cnt += 1
                            await asyncio.sleep(0.5)
                        except BotBlocked:
                            await db.delete_user(j)
                            file.write(f'user with id {j} blocked the bot. user was deleted from db\n')
                        except Exception as e:
                            file.write(f"{e}\n")
                    else:
                        user_subjects = await db.get_users_subjects_names(j)
                        for sub in subjects:
                            if sub in user_subjects:
                                try:
                                    await bot.send_photo(chat_id=j, photo=photo.file_id, caption=message.caption, parse_mode="MARKDOWN")
                                    file.write(f'sent photo to user with id {j}\n')
                                    cnt += 1
                                    await asyncio.sleep(0.5)
                                except BotBlocked:
                                    await db.delete_user(j)
                                    file.write(f'user with id {j} blocked the bot. user was deleted from db\n')
                                except Exception as e:
                                    file.write(f"{e}\n")
                                break
        elif message.content_type == 'video':
            video_id = message.video.file_id
            video = await bot.get_file(video_id)
            for i in await db.get_all_users():
                for j in i:
                    if subjects[0].lower() == "all":
                        try:
                            await bot.send_video(chat_id=j, video=video.file_id, caption=message.caption, parse_mode="MARKDOWN")
                            file.write(f'sent video to user with id {j}\n')
                            cnt += 1
                            await asyncio.sleep(0.5)
                        except BotBlocked:
                            await db.delete_user(j)
                            file.write(f'user with id {j} blocked the bot. user was deleted from db\n')
                        except Exception as e:
                            file.write(f"{e}\n")
                    else:
                        user_subjects = await db.get_users_subjects_names(j)
                        for sub in subjects:
                            if sub in user_subjects:
                                try:
                                    await bot.send_video(chat_id=j, video=video.file_id, caption=message.caption, parse_mode="MARKDOWN")
                                    file.write(f'sent video to user with id {j}\n')
                                    cnt += 1
                                    await asyncio.sleep(0.5)
                                except BotBlocked:
                                    await db.delete_user(j)
                                    file.write(f'user with id {j} blocked the bot. user was deleted from db\n')
                                except Exception as e:
                                    file.write(f"{e}\n")
                                break
        else:
            for i in await db.get_all_users():
                for j in i:
                    if subjects[0].lower() == "all":
                        try:
                            await bot.send_message(chat_id=j, text=message.text, parse_mode="MARKDOWN")
                            file.write(f'sent message to user with id {j}\n')
                            cnt += 1
                            await asyncio.sleep(0.5)
                        except BotBlocked:
                            await db.delete_user(j)
                            file.write(f'user with id {j} blocked the bot. user was deleted from db\n')
                        except Exception as e:
                            file.write(f"{e}\n")
                    elif subjects[0].lower() == "not_reg" and (await db.get_user_registration_status(j) is False):
                        try:
                            await bot.send_message(chat_id=j, text=message.text, parse_mode="MARKDOWN")
                            file.write(f'sent message to user with id {j}\n')
                            cnt += 1
                            await asyncio.sleep(0.5)
                        except BotBlocked:
                            await db.delete_user(j)
                            file.write(f'user with id {j} blocked the bot. user was deleted from db\n')
                        except Exception as e:
                            file.write(f"{e}\n")
                    else:
                        user_subjects = await db.get_users_subjects_names(j)
                        for sub in subjects:
                            if sub in user_subjects:
                                try:
                                    await bot.send_message(chat_id=j, text=message.text, parse_mode="MARKDOWN")
                                    file.write(f'sent message to user with id {j}\n')
                                    cnt += 1
                                    await asyncio.sleep(0.5)
                                except BotBlocked:
                                    await db.delete_user(j)
                                    file.write(f'user with id {j} blocked the bot. user was deleted from db\n')
                                except Exception as e:
                                    file.write(f"{e}\n")
                                break
        await message.reply("Сообщения отправлены")
        file.write(f"Sent to {cnt} users")
        file.close()
        document = open("log_mail.txt", 'rb')
        await bot.send_document(chat_id=-1001928271501, document=document, caption="Логи mail")
        document.close()
        open('log_mail.txt', 'w').close()
        await state.finish()


# следующие 3 функции: сохранение пользователей и их отправка
async def save_users():
    res = await db.get_all_users_info()
    with open('users_info.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(res)


@dp.message_handler(commands=['save_users'])
async def send_users(message):
    if message.chat.id == -1001928271501:
        await save_users()
        document = open("users_info.csv", 'rb')
        await bot.send_document(chat_id=-1001928271501, document=document, caption="users_info")
        document.close()
        open('users_info.csv', 'w').close()


async def send_users_everyweek():
    await save_users()
    document = open("users_info.csv", 'rb')
    await bot.send_document(chat_id=-1001928271501, document=document, caption="users_info")
    document.close()
    open('users_info.csv', 'w').close()


@dp.message_handler(content_types=['text'])
@analytics_messages
async def trash_msg(message):
    if message.chat.id != -1001928271501:
        if await db.get_user_registration_status(message.chat.id) is True:
            new_menu = await create_main_menu()
            await bot.send_message(chat_id=message.chat.id, text="❌ Неизвестная команда, пожалуйста, воспользуйтесь кнопками", reply_markup=new_menu)


# рассылка раз в сутки
scheduler.add_job(mailing, 'cron', hour=9, minute=30, args=[bot, subject_names])

async def on_startup(_):
    print("Start Bot!")
    logger.info("start bot")
    await bot.send_message(chat_id=-1001928271501, text=f'Бот запущен')


async def on_shutdown(_):
    message = f'total messages: {total_messages}\n'
    all_users = await db.get_all_users()
    message += f'in bd: {len(all_users)}\n'
    message += f'new users: {count_new_users}\n'
    for key, val in activity.items():
        message += f"{key} - {val}   "
    
    await bot.send_message(chat_id=-1001928271501, text=f'Данные:\n' + message)
    await goodbye()
    print("Bot stopped")
    logger.info("bot stopped")
    await bot.send_message(chat_id=-1001928271501, text=f'Бот остановлен')


# запускаем приложение и расслыку
if __name__ == "__main__":
    scheduler.start()
    dp.middleware.setup(ThrottlingMiddleware())
    executor.start_polling(dp, 
                           on_startup=on_startup,
                           on_shutdown=on_shutdown)
