"""Аналитика"""
from aiogram import types

import csv
import pandas as pd
import matplotlib.pyplot as plt

from matplotlib.backends.backend_pdf import PdfPages


async def create_title(text):
    title_page = plt.figure(figsize=(10,7))
    title_page.clf()
    txt = text
    title_page.text(0.5,0.5, txt, transform=title_page.transFigure, size=24, ha="center", weight='bold')
    page.savefig()
    plt.close()


async def create_first_page(db):
    with open("analytics.csv") as file:
        reader = csv.DictReader(file)
        last_row = []
        for row in reader:
            last_row = row
        print(last_row)
    count_users = len(await db.get_all_users())
    count_users_ended_registration = len(await db.get_users_ended_registration())
    count_users_not_ended_registration = len(await db.get_users_not_ended_registration())
    message = f"Данные за сегодня ({last_row['date']})\n\n"
    message += f"Количество пользователей: {count_users}\n"
    message += f"Из них завершило регистрацию: {count_users_ended_registration}\n"
    message += f"Не завершило: {count_users_not_ended_registration}\n"
    message += f"Подписалось пользователей: {last_row['new_users']}\n"
    message += f"Отписалось пользователей: {last_row['deleted_users']}\n"
    message += f"Сообщений пришло: {last_row['total_messages']}"
    first_page = plt.figure(figsize=(10,7))
    first_page.clf()
    first_page.text(0.5,0.5, message, transform=first_page.transFigure, size=24, ha="center")
    page.savefig()
    plt.close()


# отправка аналитики в чат техподдержки
async def send_analytics(bot, db):
    global page
    page = PdfPages("analytics.pdf")
    plt.style.use('ggplot')
    # создание диаграмм
    await create_first_page(db)
    await visual_user_count()
    await visual_new_users()
    await visual_deleted_users()
    await visual_activity()
    await visual_total_messages()
    await visual_subjects(db)
    await visual_classes(db)
    page.close()

    media = types.MediaGroup()
    media.attach(types.InputMediaDocument(open("analytics.pdf", 'rb')))
    media.attach(types.InputMediaDocument(open("analytics.csv", 'rb')))
    media.attach(types.InputMediaDocument(open("analytics_data.json", 'rb')))
    await bot.send_media_group(chat_id=-1001928271501, media=media)
    cnt_mailing_olympiads, cnt_mailing_hackathons, cnt_mailing_programming = await db.get_true_count()
    await bot.send_message(chat_id=-1001928271501, text=f'кол-во пользователей с включённой рассылкой:\nолимпиад - {cnt_mailing_olympiads}\nхакатонов - {cnt_mailing_hackathons}\nпрограммирования - {cnt_mailing_programming}')

# построение графиков: количество пользователей в бд
async def visual_user_count():
    await create_title("Количество пользователей")
    data = pd.read_csv('analytics.csv', usecols=["date", "count_users"])
    # за всё время
    data.plot("date", "count_users", style={'count_users': '#FF9E00'}, lw=2)
    plt.title("Количество пользователей за всё время", fontsize=12, fontweight='bold', pad=20)
    plt.xticks(fontsize=7, fontweight='bold')
    plt.xlabel("")
    page.savefig(plt.gcf())
    # за последние 20 дней
    data[-30:].plot("date", "count_users", style={'count_users': '#FF9E00'}, lw=2)
    plt.title("Количество пользователей за последний месяц", fontsize=12, fontweight='bold', pad=20)
    plt.xticks(fontsize=7, fontweight='bold')
    plt.xlabel("")
    page.savefig(plt.gcf())
    # за последние 7 дней
    data[-7:].plot("date", "count_users", style={'count_users': '#FF9E00'}, marker='.', lw=2)
    plt.title("Количество пользователей за последние 7 дней", fontsize=12, fontweight='bold', pad=20)
    plt.xticks(fontsize=7, fontweight='bold')
    plt.xlabel("")
    page.savefig(plt.gcf())
    plt.clf()


# построение графиков: количество новых пользователей
async def visual_new_users():
    await create_title("Новые пользователи")
    data = pd.read_csv('analytics.csv', usecols=["date", "new_users"])
    data.plot("date", "new_users", style={'new_users': '#00A67C'})
    plt.title("Новые пользователи за всё время", fontsize=12, fontweight='bold', pad=20)
    plt.xticks(fontsize=7, fontweight='bold')
    plt.xlabel("")
    page.savefig(plt.gcf())

    data[-30:].plot("date", "new_users", style={'new_users': '#00A67C'})
    plt.title("Новые пользователи за последний месяц", fontsize=12, fontweight='bold', pad=20)
    plt.xticks(fontsize=7, fontweight='bold')
    plt.xlabel("")
    page.savefig(plt.gcf())

    data[-7:].plot("date", "new_users", title="Новые пользователи за последнюю неделю", style={'new_users': '#00A67C'}, marker='.')
    plt.title("Новые пользователи за последнюю неделю", fontsize=12, fontweight='bold', pad=20)
    plt.xticks(fontsize=7, fontweight='bold')
    plt.xlabel("")
    page.savefig(plt.gcf())
    plt.clf()


# построение графиков: количество отписавшихся пользователей
async def visual_deleted_users():
    await create_title("Количество отписавшихся пользователей")
    data = pd.read_csv('analytics.csv', usecols=["date", "deleted_users"])
    data.plot("date", "deleted_users", style={'deleted_users': '#F73E5F'})
    plt.title("Отписавшиеся пользователи за всё время", fontsize=12, fontweight='bold', pad=20)
    plt.xticks(fontsize=7, fontweight='bold')
    plt.xlabel("")
    page.savefig(plt.gcf())

    data[-30:].plot("date", "deleted_users", style={'deleted_users': '#F73E5F'})
    plt.title("Отписавшиеся пользователи за последний месяц", fontsize=12, fontweight='bold', pad=20)
    plt.xticks(fontsize=7, fontweight='bold')
    plt.xlabel("")
    page.savefig(plt.gcf())

    data[-7:].plot("date", "deleted_users", style={'deleted_users': '#F73E5F'}, marker='.')
    plt.title("Отписавшиеся пользователи за последнюю неделю", fontsize=12, fontweight='bold', pad=20)
    plt.xticks(fontsize=7, fontweight='bold')
    plt.xlabel("")
    page.savefig(plt.gcf())
    plt.clf()


# построение графиков: активность
async def visual_activity():
    await create_title("Активность")
    cols = []
    for i in range(24):
        cols.append(f"activity_{i}")
    data = pd.read_csv('analytics.csv', usecols=cols)
    last_row = []
    avarage_activity_7_days = [0] * 24
    avarage_activity_30_days = [0] * 24
    avarage_activity = [0] * 24
    for i in range(24):
        cur_list = data[f"activity_{i}"].to_list()
        last_row.append(cur_list[-1])
        avarage_activity_7_days[i] = sum(cur_list[-7:]) / 7
        avarage_activity_30_days[i] = sum(cur_list[-30:]) / 30
        avarage_activity[i] = sum(cur_list) / len(cur_list)
    print(avarage_activity)
    indexes = [i for i in range(24)]
    print(last_row)
    bar = plt.bar(indexes, last_row, color="#35D2AB")
    plt.title("Активность за сегодня", fontsize=12, fontweight='bold', pad=20)
    plt.xticks(fontsize=7, fontweight='bold', ticks=[i for i in range(24)])
    page.savefig(plt.gcf())
    plt.clf()

    plt.bar(indexes, avarage_activity_7_days, color="#35D2AB")
    plt.title("Средняя активность за последнюю неделю", fontsize=12, fontweight='bold', pad=20)
    plt.xticks(fontsize=7, fontweight='bold', ticks=[i for i in range(24)])
    page.savefig(plt.gcf())
    plt.clf()

    plt.bar(indexes, avarage_activity_30_days, color="#35D2AB")
    plt.title("Средняя активность за последний месяц", fontsize=12, fontweight='bold', pad=20)
    plt.xticks(fontsize=7, fontweight='bold', ticks=[i for i in range(24)])
    page.savefig(plt.gcf())
    plt.clf()

    bar = plt.bar(indexes, avarage_activity, color="#35D2AB")
    plt.title("Средняя активность за всё время", fontsize=12, fontweight='bold', pad=20)
    plt.xticks(fontsize=7, fontweight='bold', ticks=[i for i in range(24)])
    page.savefig(plt.gcf())
    plt.clf()


# построение графиков: количество сообщений
async def visual_total_messages():
    await create_title("Сообщения (запросы)")
    data = pd.read_csv('analytics.csv', usecols=["date", "total_messages"])
    data.plot("date", "total_messages", style={'total_messages': '#FF9E00'}, lw=2)
    plt.title("Количество сообщений за всё время", fontsize=12, fontweight='bold', pad=20)
    plt.xlabel("")
    plt.xticks(fontsize=7, fontweight='bold')
    page.savefig(plt.gcf())
    plt.clf()

    data[-30:].plot("date", "total_messages", style={'total_messages': '#FF9E00'}, lw=2)
    plt.title("Количество сообщений за последний месяц", fontsize=12, fontweight='bold', pad=20)
    plt.xlabel("")
    plt.xticks(fontsize=7, fontweight='bold')
    page.savefig(plt.gcf())
    plt.clf()

    data[-7:].plot("date", "total_messages", style={'total_messages': '#FF9E00'}, lw=2, marker='.')
    plt.title("Количество сообщений за последнюю неделю", fontsize=12, fontweight='bold', pad=20)
    plt.xlabel("")
    plt.xticks(fontsize=7, fontweight='bold')
    page.savefig(plt.gcf())
    plt.clf()


# построение графиков: выбранные предметы
async def visual_subjects(db):
    await create_title("Предметы и классы")
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
    tups.sort(key=lambda x: x[1])
    keys = []
    values = []
    for i in range(len(tups)):
        key, val = tups[i]
        keys.append(key)
        values.append(val)
    fig, ax = plt.subplots(figsize=(15,8))
    bars = plt.barh(keys, values, color="#35D2AB")
    plt.title("Выбранные преметы", fontsize=16, fontweight='bold', pad=20)
    plt.xticks(fontsize=7, fontweight='bold')
    page.savefig(plt.gcf())
    plt.clf()


# построение графиков: классы пользователей
async def visual_classes(db):
    all_users = await db.get_all_users()
    d_classes = {}
    for i in range(8, 12):
        d_classes[str(i)] = 0
    d_classes["Не школьник"] = 0
    for user in all_users:
        user_class = await db.get_user_class(user[0])
        if user_class is not None:
            d_classes[user_class] += 1
    keys = d_classes.keys()
    values = d_classes.values()

    fig, ax = plt.subplots()
    ax.pie(values, labels=keys, autopct='%1.1f%%', wedgeprops=dict(width=0.6), colors=["#35D2AB", "#FFA773", "#F73E5F", "#006C51", "#1959d1"])
    ax.axis("equal")
    ax.legend(loc='best')
    plt.title("Классы пользователей", fontsize=16, fontweight='bold', pad=20)
    page.savefig(plt.gcf())