"""Логика"""
import asyncio
import aiohttp
import time

from parse_olympiads import get_olympiads_updates, parse_camps, parse_codeforces_rounds, parse_leetcode, get_codechef_rounds
from parse_hackathons import add, check
from db import Database, check_class
from markup import create_olimpiads_markup, create_olimpiads_markup_for_teachers

from aiogram.utils.exceptions import BotBlocked
from loguru import logger


# db = Database()


logger.add("debug.log", format="{time} {level} {message}", filter=lambda record: record["level"].name == "DEBUG")
logger.add("info.log", format="{time} {level} {message}", filter=lambda record: record["level"].name == "INFO")
logger.add("error.log", format="{time} {level} {message}", filter=lambda record: record["level"].name == "ERROR")

"""Проверка"""
# проверка. Пытаемся отправитб сообщение
# если бот заблокирован - пользователя отписался, удаляем его из БД
async def send_mailing_with_check(chat_id, text, bot, db):
    try:
        await bot.send_message(chat_id=chat_id, text=text,
                    parse_mode='Markdown', disable_web_page_preview=True)
        await asyncio.sleep(0.3)
        return True
    except BotBlocked:
        with open("log_mailing.txt", 'a') as file:
            file.write(f'WARNING: it seems user with id {chat_id} blocked the bot (?)\n')
        await db.delete_user(chat_id)
        return False
    except Exception as e:
        with open("log_mailing.txt", 'a') as file:
            file.write(f'ERROR: error {e}\n')
        return True


"""Списки"""
# отправка списка с актуальными хакатонами
async def list_of_hacks(chat_id, bot, db):
    hacks = await db.take_hackathons()
    if len(hacks) > 0:
        for hack in hacks:
            try:
                hack = hack.replace('`', '')
                hack = hack.replace('*', '')
                hack = hack.replace('_', '')
                await bot.send_message(chat_id=chat_id, text=f"{hack}", parse_mode='Markdown', disable_web_page_preview=True)
            except Exception as e:
                logger.error(e)
    else:
        await bot.send_message(chat_id=chat_id, 
                         text="Увы, но сейчас нет актуальных хакатонов. "+ \
                         "Но Вы можете включить рассылку, и как только хакатоны появятся - мы Вас уведомим!")
        

# отправка списка с актуальными олимпиадами
async def list_of_olympiads(chat_id, bot, db):
    if await db.check_teacher_status(chat_id):
        select_markup = await create_olimpiads_markup_for_teachers()
    else:
        select_markup = await create_olimpiads_markup(chat_id, db)
    await bot.send_message(chat_id=chat_id, text="Списки по какому предмету вас интересуют?", 
                           reply_markup=select_markup)
    
    
async def show_subject_olympiads(chat_id, bot, db, subject_name):
    user_class = await db.get_user_class(chat_id)
    result = await db.take_olympiads(subject_name, user_class)
    if len(result.keys()):
        await bot.send_message(chat_id=chat_id, text=f"*{subject_name}*", 
                            parse_mode='Markdown', disable_web_page_preview=True)
    for key, value in result.items():
        await bot.send_message(chat_id=chat_id, text=value, parse_mode='Markdown', disable_web_page_preview=True)
    await list_of_olympiads(chat_id, bot, db)

    

async def list_of_camps(chat_id, bot, db):
    user_subjects = await db.get_users_subjects_names(chat_id)
    camps = await db.get_all_camps()
    if len(camps):
        mes = ""
        flag = False
        for camp in camps:
            cur_id, name, classes, subjects, site, state, link = camp
            state = state.replace('`', '')
            state = state.replace('*', '')
            state = state.replace('_', '')
            for elem in subjects.split(', '):
                if await db.get_subjects_names_from_id(elem) in user_subjects:
                    flag = True
                    mes += f"[{name}]({site})\n"
                    mes += f"{state}\n\n"
                    break
        if flag:
            await bot.send_message(chat_id=chat_id, text="*Олимпиадные лагеря*", parse_mode='Markdown', disable_web_page_preview=True)
            await bot.send_message(chat_id=chat_id, text=mes, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            await bot.send_message(chat_id=chat_id, text="На данный момент по выбранным предметам нет лагерей")

async def codeforces_rounds(chat_id, bot, db):
        codeforces_rounds = await db.get_all_codeforces_rounds()
        codeforces_rounds.sort(key=lambda x: x[0])
        message = '*Codeforces-раунды*\n'
        message += f'[Ссылка на ресурc](https://codeforces.com/contests)' + '\n'
        for cf_round in codeforces_rounds:
            _, platform, name, date_time, registration_state = cf_round
            message += name + '\n'
            message += '🕓 ' + date_time + '\n'
            message += registration_state + '\n\n'
        if message == '*Codeforces-раунды*\n' + f'[Ссылка на ресурc](https://codeforces.com/contests)' + '\n':
            message = "Текущих раундов нет"
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown', disable_web_page_preview=True)


# вывод codechef-раундов
async def codechef_rounds(chat_id, bot, db):
    codechef = await db.get_all_codechef_rounds()
    codechef.sort(key=lambda x: int(x[2].split()[-1]))
    # print("codechef: ", codechef)
    message = '*CodeChef-раунды*\n'
    message += f'[Ссылка на ресурc](https://www.codechef.com/contests)' + '\n'
    for cc_round in codechef:
        name, date_time, registration_state = cc_round
        message += name + '\n'
        message += '🕓 ' + date_time + '\n'
        message += registration_state + '\n\n'
    if message == '*CodeChef-раунды*\n' + f'[Ссылка на ресурc](https://www.codechef.com/contests)' + '\n':
        message = "Текущих раундов нет"
    await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown', disable_web_page_preview=True)


async def leetcode_rounds(chat_id, bot, db):
    leetcode_rounds = await db.get_all_leetcode_rounds()
    message = '*LeetCode-раунды*\n\n'
    for leet_round in leetcode_rounds:
        name, date_time, registration_state = leet_round
        message += name + '\n'
        message += '🕓 ' + date_time + '\n'
        message += f'[Ссылка на ресурc]({registration_state})' + '\n\n'
    if message == '*LeetCode-раунды*\n\n':
        message = "Текущих раундов нет"
    await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown', disable_web_page_preview=True)
        
        
"""Рассылка"""
@logger.catch
async def mailing(bot, subject_names):
    logger.info("begin mailing")
    db = Database()
    await db.async_init()
    start_timestamp = time.time()
    event_messages = []
    # получаем новые хакатоны
    try:
        news = await check(db)
    except Exception as e:
        news = []
        with open("log_mailing.txt", 'a') as file:
            file.write(f"ERROR check() hackathons: {e}")
    # формируем сообщение
    for event in news:
        text = f"[{event['name']}]({event['link']}) \n"
        if 'place' in event:
            text += 'Место проведения: ' + event['place'] + '\n'
        if 'Хакатон' in event:
            text += 'Дата проведения: ' + event['Хакатон'] + '\n'
        if 'Регистрация' in event:
            text += 'Дата регистрации: ' + event['Регистрация'] + '\n'
        if 'Технологический фокус' in event:
            text += 'Технологический фокус: ' + event['Технологический фокус'] + '\n'
        if 'Целевая аудитория' in event:
            text += 'Целевая аудитория: ' + event['Целевая аудитория'] + '\n'
        if 'Призовой фонд' in event:
            text += 'Приз: ' + event['Призовой фонд'] + '\n'
        text = text.replace('`', '')
        text = text.replace('*', '')
        text = text.replace('_', '')
        event_messages.append(text)
    # добавляем хакатоны в бд
    try:
        await add(db)
    except Exception as e:
        with open("log_mailing.txt", 'a') as file:
            file.write(f"ERROR add() hackathons: {e}")
    # в словаре d хранятся id олимпиад, у которых обновился статус. Ключи словаря - навзания предметов
    d = {}
    
    print(subject_names)
    # пасрим обновления
    for sub in subject_names:
        print("subject: ", sub)
        if sub == "Генетика":
            continue
        try:
            d[sub] = await get_olympiads_updates(sub, db)
        except Exception as e:
            d[sub] = {"new": [], "remind": {"1": [], "3": [], "7": [],"14": []}}
            
            with open("log_mailing.txt", 'a') as file:
                file.write(f"ERROR (parse_olympiads): {e}")
    try:
        camps = await parse_camps(db)
    except Exception as e:
        camps = []
        with open("log_mailing.txt", 'a') as file:
            file.write(f"ERROR (parse_camps): {e}")
    try:
        codeforces_rounds = await parse_codeforces_rounds(db)
    except Exception as e:
        codeforces_rounds = []
        with open("log_mailing.txt", 'a') as file:
            file.write(f"ERROR (parse_codeforces): {e}")
    try:
        codechef_rounds = await get_codechef_rounds(db)
    except Exception as e:
        codechef_rounds = []
        with open("log_mailing.txt", 'a') as file:
            file.write(f"ERROR (parse_codechef): {e}")
    try:
        leetcode_rounds = await parse_leetcode(db)
    except Exception as e:
        leetcode_rounds = []
        with open("log_mailing.txt", 'a') as file:
            file.write(f"ERROR (parse_leetcode): {e}")
    await asyncio.sleep(3)
    print(d)
    
    users = await db.get_all_users()
    cnt_sent = 0
    # проходим по всем пользователям
    for chat_id in users:
        chat_id = chat_id[0]
        # рассылка возможна только есть пользователь закночил регистрацию
        if await db.get_user_registration_status(chat_id) is True:
            # олимпиадная рассылка
            try:
                # await bot.send_message(chat_id=-1001928271501, text=f'пользователю с id {chat_id} начинаем отправлять рассылку')
                with open("log_mailing.txt", 'a') as file:
                    file.write(f'INFO: user with id {chat_id}: begin mailig\n')
            except Exception as e:
                print("ERROR!", e)
                # await bot.send_message(chat_id=-1001928271501, text=f'пользователю с id {chat_id}: {e}')
                with open("log_mailing.txt", 'a') as file:
                    file.write(f'ERROR: user with id {chat_id}: {e}\n')
            # finally:
            #     await asyncio.sleep(0.1)
            user_subjects = await db.get_users_subjects_names(chat_id)
            if await db.get_mailing_olympiads_state(chat_id) is True:
                user_class = await db.get_user_class(chat_id)
                flag = False
                olymp_message = "*Олимпиадные новости*\n"
                # проходимся по всем предметам, которые выбрал данный пользователь
                for subject in user_subjects:
                    print("!!!!!")
                    print(subject)
                    print(d)
                    new_olymps = d[subject]["new"]
                    # если есть хотя бы одно обновление
                    if len(new_olymps):
                        arr = []
                        for el in new_olymps:
                            name = await db.get_olympiad_name_by_id(el)
                            state = await db.get_olympiad_state_by_id(el)
                            olymp_name = await db.get_olympiad_name_by_id(el)
                            classes = await db.get_olympiad_classes(olymp_name, subject)
                            site = await db.get_olympiad_site(olymp_name, subject)
                            # добавляем олимпиаду в рассылку, если она подходит по классу
                            if await check_class(user_class, classes):
                                arr.append(f"[{name}]({site}) \n{state}")  # f"[{name}]({site}) \n"
                        if len(arr):
                            olymp_message += f"*{subject}*\n"
                            olymp_message += '\n\n'.join(arr) + "\n\n"
                if olymp_message != "*Олимпиадные новости*\n":
                    flag_success = await send_mailing_with_check(chat_id, olymp_message, bot, db)
                    if flag_success is False:
                        with open("log_mailing.txt", 'a') as file:
                            file.write(f'INFO: user with id {chat_id}: break on olympiads\n')
                        continue

                # olymp_message = "*Напоминаем:*\n"
                remind_days = (await db.get_user_remind_days(chat_id))[0][0].split()
                remind_days.sort(key=lambda x: int(x))
                for day in remind_days:
                    current_message = f"*Осталось дней: {day}*\n"
                    for subject in user_subjects:
                        new_olymps = d[subject]["remind"][day]
                        # если есть хотя бы одно обновление
                        if len(new_olymps):
                            arr = []
                            for el in new_olymps:
                                name = await db.get_olympiad_name_by_id(el)
                                state = await db.get_olympiad_state_by_id(el)
                                olymp_name = await db.get_olympiad_name_by_id(el)
                                classes = await db.get_olympiad_classes(olymp_name, subject)
                                site = await db.get_olympiad_site(olymp_name, subject)
                                # добавляем олимпиаду в рассылку, если она подходит по классу
                                if await check_class(user_class, classes):
                                    arr.append(f"[{name}]({site}) \n{state}")  # f"[{name}]({site}) \n"
                            if len(arr):
                                current_message += f"*{subject}*\n"
                                current_message += '\n\n'.join(arr) + "\n\n"
                    if current_message != f"*Осталось дней: {day}*\n":
                        flag_success = await send_mailing_with_check(chat_id, current_message, bot, db)
                        if flag_success is False:
                            with open("log_mailing.txt", 'a') as file:
                                file.write(f'INFO: user with id {chat_id}: break on remind olympiads\n')
                            continue
                mes = ''
                flag = False
                print("capms")
                print(camps)
                for camp in camps["new"]:
                    print("->", camp)
                    name, classes, subjects, site, state = camp
                    # flag = False
                    for elem in subjects:
                        if await db.get_subjects_names_from_id(elem) in user_subjects:
                            flag = True
                            mes += f"[{name}]({site}) \n"
                            mes += f"{state}\n\n"
                            break
                if len(remind_days):
                    for camp in camps["remind"]:
                        print("remind ->", camp)
                        name, classes, subjects, site, state = camp

                        for elem in subjects:
                            if await db.get_subjects_names_from_id(elem) in user_subjects:
                                flag = True
                                mes += f"[{name}]({site}) \n"
                                mes += f"{state}\n\n"
                                break
                if flag:
                    flag_success = await send_mailing_with_check(chat_id, "*Олимпиадные лагеря*\n" +  mes, bot, db)
                    if flag_success is False:
                        with open("log_mailing.txt", 'a') as file:
                            file.write(f'INFO: user with id {chat_id}: break on camps\n')
                        continue
                else:
                    print("пока обновлений нет")
            try:
                with open("log_mailing.txt", 'a') as file:
                    file.write(f'INFO: user with id {chat_id}: olympiads sent\n')
            except Exception as e:
                print("ERROR!", e)
                with open("log_mailing.txt", 'a') as file:
                    file.write(f'ERROR: user with id: {chat_id}: {e}\n')
            # рассылка тренировок
            if await db.get_mailing_status_of_programming(chat_id) is True:
            # рассылка codeforces-раундов
                message = '*Codeforces-раунды*\n'
                message += f'[Ссылка на ресурc](https://codeforces.com/contests)' + '\n'
                for cf_round in codeforces_rounds:
                    name, date_time, registration_state = cf_round
                    message += name + '\n'
                    message += '🕓 ' + date_time + '\n'
                    message += registration_state + '\n\n'
                if message != '*Codeforces-раунды*\n' + f'[Ссылка на ресурc](https://codeforces.com/contests)' + '\n':
                    flag_success = await send_mailing_with_check(chat_id, message, bot, db)
                    if flag_success is False:
                        with open("log_mailing.txt", 'a') as file:
                            file.write(f'INFO: user with id {chat_id}: break on codeforces\n')
                        continue
                # рассылка codechef-раундов
                message = '*CodeChef-раунды*\n'
                message += f'[Ссылка на ресурc](https://www.codechef.com/contests)' + '\n'
                for cc_round in codechef_rounds:
                    name, date_time, registration_state = cc_round
                    message += name + '\n'
                    message += '🕓 ' + date_time + '\n'
                    message += registration_state + '\n\n'
                if message != '*CodeChef-раунды*\n' + f'[Ссылка на ресурc](https://www.codechef.com/contests)' + '\n':
                    flag_success = await send_mailing_with_check(chat_id, message, bot, db)
                    if flag_success is False:
                        with open("log_mailing.txt", 'a') as file:
                            file.write(f'INFO: user with id {chat_id}: break on codechef\n')
                        continue
                # рассылка leetcode-раундов
                message = '*LeetCode-раунды*\n\n'
                for leet_round in leetcode_rounds:
                    name, date_time, registration_state = leet_round
                    message += name + '\n'
                    message += '🕓 ' + date_time + '\n'
                    message += f'[Ссылка на ресурc]({registration_state})' + '\n\n'
                if message != '*LeetCode-раунды*\n\n':
                    flag_success = await send_mailing_with_check(chat_id, message, bot, db)
                    if flag_success is False:
                        with open("log_mailing.txt", 'a') as file:
                            file.write(f'INFO: user with id {chat_id}: break on leetcode\n')
                        continue
            try:
                with open("log_mailing.txt", 'a') as file:
                    file.write(f'INFO: user with id {chat_id}: contests sent\n')
            except Exception as e:
                print("ERROR!", e)
                with open("log_mailing.txt", 'a') as file:
                    file.write(f'ERROR: user with id {chat_id}: {e}\n')
            # рассылка хакатонов
            if await db.get_mailing_hackathons_state(chat_id) is True:
                print(chat_id)
                try:
                    if len(event_messages) > 0:
                        print(chat_id)
                        a = '\n'.join(event_messages)
                        flag_success = await send_mailing_with_check(chat_id, f"*Новые хакатоны*\n \n{a}", bot, db)
                        if flag_success is False:
                            with open("log_mailing.txt", 'a') as file:
                                file.write(f'INFO: user with id {chat_id}: break on hackathons\n')
                            continue
                except Exception as ex:
                    print("hack", ex)
            try:
                with open("log_mailing.txt", 'a') as file:
                    file.write(f'INFO: user with id {chat_id}: everything was sent\n')
            except Exception as e:
                print("ERROR!", e)
                with open("log_mailing.txt", 'a') as file:
                    file.write(f'ERROR: user with id {chat_id}: {e}\n')
            cnt_sent += 1
    print("time: ", round(time.time() - start_timestamp, 2))
    try:
        with open("log_mailing.txt", 'a') as file:
            file.write(f'INFO: mailing is completed. To {cnt_sent} users\n')
    except Exception as e:
        print("ERROR!", e)
        with open("log_mailing.txt", 'a') as file:
            file.write(f'ERROR: user with id {chat_id}: {e}\n')
    document = open("log_mailing.txt", 'rb')
    await bot.send_document(chat_id=-1001928271501, document=document, caption="Логи рассылки")
    document.close()
    open('log_mailing.txt', 'w').close()
    await db.connection.close()


"""Отправка логов"""
@logger.catch
async def send_logs(bot):
    try:
        document = open("info.log", 'rb')
        await bot.send_document(chat_id=-1001928271501, document=document, caption="Логи (info)")
        document.close()
    except Exception:
        await bot.send_message(chat_id=-1001928271501, text="Логи (info) - пусто")
    finally:
        open('info.log', 'w').close()

    try:
        document = open("warnings.log", 'rb')
        await bot.send_document(chat_id=-1001928271501, document=document, caption="Логи (warnings)")
        document.close()
    except Exception:
        await bot.send_message(chat_id=-1001928271501, text="Логи (warnings) - пусто")
    finally:
        open('warnings.log', 'w').close()

    try:
        document = open("error.log", 'rb')
        await bot.send_document(chat_id=-1001928271501, document=document, caption="Логи (errors)")
        document.close()
    except Exception:
        await bot.send_message(chat_id=-1001928271501, text="Логи (errors) - пусто")
    finally:
        open('error.log', 'w').close()