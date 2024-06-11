import os

from dotenv import load_dotenv
from os.path import join, dirname
from pprint import pprint

import psycopg



# получение данных из env.env
def get_from_env(key):
    print("get..")
    dotenv_path = join(dirname(__file__), 'env.env')
    load_dotenv(dotenv_path)
    return os.environ.get(key)


# проверка, подходит ли олимпиада пользователю по классу
async def check_class(user_class, olymp_classes):
    if "классы" in olymp_classes:  # несколько классов
        delta, rest = olymp_classes.split()
        left, right = delta.split('–')
        # проверяем, что класс пользователя лежим в промежутке
        if user_class is None:
            return False
        return int(left) <= int(user_class) <= int(right)
    else:
        # один класс
        cur_class, rest = olymp_classes.split()
        return int(cur_class) == user_class  # проверяем совпадение классов


# класс для работы с БД
class Database:
    def __init__(self):
        print("init")
        pass

    async def async_init(self):
        self.connection = await psycopg.AsyncConnection.connect(user='XXXX', 
                                                    password='XXXX', 
                                                    dbname='XXXX',
                                                    host='XXXX',
                                                    port='XXXX')
        self.cursor = self.connection.cursor() 
            
    # subjects
    # провека существования предмета в таблице Subjects
    async def subjects_exists(self, subject_name):
        await self.cursor.execute(f"""SELECT * FROM Subjects WHERE Subjects.name = '{subject_name}'""")
        try:
            result = await self.cursor.fetchone()[0]
        except:
            result = None
        return result
    
    
    async def count_subs(self, chat_id):
        await self.cursor.execute(f"""SELECT subs FROM Users WHERE user_id = '{chat_id}'""")
        subs = await self.cursor.fetchone()
        subs = subs[0]
        print(subs)
        if subs == None:
            return 0
        subs = subs.split(', ')
        count = len(subs)
        print(count)
        return count
        
    
    
    # добавление предмета (только если его нет)
    async def add_subject(self, subject_name, subject_html_name):
        if self.subjects_exists(subject_name) is None:  # если такого предмета нет
            await self.cursor.execute(f"""INSERT INTO Subjects (name, html_name) values('{subject_name}', '{subject_html_name}')""")
            await self.connection.commit()
    
    # id предмета по названию
    async def get_subjects_id(self, subject_name):
        print("get_subjects_id: ", subject_name)
        await self.cursor.execute(f"""SELECT id FROM Subjects WHERE name = '{subject_name}'""")
        result = await self.cursor.fetchone()
        return result[0]
    
    # получение названия предмета по id
    async def get_subjects_names_from_id(self, id):
        await self.cursor.execute(f"""SELECT name FROM Subjects WHERE id = '{id}'""")
        result = await self.cursor.fetchone()
        return result[0]
    
    # названия всех предметов
    async def get_subject_names(self):
        await self.cursor.execute(f"""SELECT name FROM Subjects""")
        subjects = await self.cursor.fetchall()
        ans = []
        for el in subjects:
            ans.append(el[0])
        return ans
    
    # получение html-названия предмета
    async def get_subject_html(self, subject_name):
        await self.cursor.execute(f"""SELECT html_name FROM Subjects WHERE name = '{subject_name}'""")
        result = await self.cursor.fetchone()
        return result[0]
    
    # olympiads
    # провека существования олимпиады в таблице Olympiads.
    # Олимпиады считаются одинаковыми, если у них равны названия и предмет
    async def olympiad_exists(self, olymp_name, subject_name):
        await self.cursor.execute(f"""SELECT * FROM Olympiads INNER JOIN Subjects 
                                                ON Olympiads.subject_id = Subjects.id
                                    WHERE Olympiads.name = '{olymp_name}' AND Subjects.name = '{subject_name}'""")
        try:
            result = await self.cursor.fetchone()
            return result[0]
        except:
            return None

    # добавление олимпиады (проверка отдельно)
    async def add_olympiad(self, olymp_name, number, profile, subject_name, level, classes, site, state, link):
        subject_id = await self.get_subjects_id(subject_name)
        await self.cursor.execute(f"""INSERT INTO Olympiads (name, number, profile, subject_id, 
                                                        level, classes, site, state, link)
                                VALUES('{olymp_name}', {number}, '{profile}', {subject_id},
                                        {level}, '{classes}', '{site}', '{state}', '{link}')""")
        await self.connection.commit()

    # id олимпиады по названию
    async def get_olympiad_id(self, olymp_name, subjects_name):
        subject_id = await self.get_subjects_id(subjects_name)
        await self.cursor.execute(f"""SELECT id FROM Olympiads
                                    WHERE name = '{olymp_name}' AND subject_id = '{subject_id}'""")
        result = await self.cursor.fetchone()
        return result[0]
    
    # состояние олимпиады
    async def get_olympiad_state(self, olymp_name, subjects_name):
        subject_id = await self.get_subjects_id(subjects_name)
        await self.cursor.execute(f"""SELECT state FROM Olympiads
                                    WHERE name = '{olymp_name}' AND subject_id = '{subject_id}'""")
        result = await self.cursor.fetchone()
        return result[0]
    
    # классы олимпиады
    async def get_olympiad_classes(self, olymp_name, subjects_name):
        subject_id = await self.get_subjects_id(subjects_name)
        await self.cursor.execute(f"""SELECT classes FROM Olympiads
                                    WHERE name = '{olymp_name}' AND subject_id = '{subject_id}'""")
        result = await self.cursor.fetchone()
        return result[0]
    
    # сайт олимпиады
    async def get_olympiad_site(self, olymp_name, subjects_name):
        subject_id = await self.get_subjects_id(subjects_name)
        await self.cursor.execute(f"""SELECT site FROM Olympiads
                                    WHERE name = '{olymp_name}' AND subject_id = '{subject_id}'""")
        result = await self.cursor.fetchone()
        return result[0]
    
    # получение названия по id
    async def get_olympiad_name_by_id(self, ol_id):
        await self.cursor.execute(f"""SELECT name FROM Olympiads
                                    WHERE id = '{ol_id}'""")
        result = await self.cursor.fetchone()
        return result[0]

     # получение состояния по id
    async def get_olympiad_state_by_id(self, ol_id):
        await self.cursor.execute(f"""SELECT state FROM Olympiads
                                    WHERE id = '{ol_id}'""")
        result = await self.cursor.fetchone()
        return result[0]

    # все олимпиады определённого предмета
    async def get_all_olympiads_of_certain_subjects(self, subject_name):
        await self.cursor.execute(f"""SELECT Olympiads.name, Olympiads.level, 
                                Olympiads.classes, Olympiads.site, Olympiads.state, Olympiads.link
                                FROM Olympiads INNER JOIN Subjects 
                                                ON Olympiads.subject_id = Subjects.id
                                    WHERE Subjects.name = '{subject_name}'""")
        result = await self.cursor.fetchall()
        return result
    
    # обновление
    # уровень
    async def update_olympiad_level(self, olymp_name, subject_name, level):
        subject_id = await self.get_subjects_id(subject_name)
        await self.cursor.execute(f"""UPDATE Olympiads 
                                SET level = '{level}'
                                WHERE name = '{olymp_name}' AND subject_id = '{subject_id}'""")
        await self.connection.commit()

    # сайт
    async def update_olympiad_site(self, olymp_name, subject_name, site):
        subject_id = await self.get_subjects_id(subject_name)
        await self.cursor.execute(f"""UPDATE Olympiads 
                                SET site = '{site}'
                                WHERE name = '{olymp_name}' AND subject_id = '{subject_id}'""")
        await self.connection.commit()
    
    # класс
    async def update_olympiad_classes(self, olymp_name, subject_name, classes):
        subject_id = await self.get_subjects_id(subject_name)
        await self.cursor.execute(f"""UPDATE Olympiads 
                                SET classes = '{classes}'
                                WHERE name = '{olymp_name}' AND subject_id = '{subject_id}'""")
        await self.connection.commit()

    # состояние
    async def update_olympiad_state(self, olymp_name, subject_name, state):
        subject_id = await self.get_subjects_id(subject_name)
        await self.cursor.execute(f"""UPDATE Olympiads 
                                SET state = '{state}'
                                WHERE name = '{olymp_name}' AND subject_id = '{subject_id}'""")
        await self.connection.commit()

    # ссылка на страницу с олимпиадой (olympiada.ru)
    async def update_olympiad_link(self, olymp_name, subject_name, link):
        subject_id = await self.get_subjects_id(subject_name)
        await self.cursor.execute(f"""UPDATE Olympiads 
                                SET link = '{link}'
                                WHERE name = '{olymp_name}' AND subject_id = '{subject_id}'""")
        await self.connection.commit()


    # список олимпиад
    async def take_olympiads(self, subject_name, user_class):
        subject_id = await self.get_subjects_id(subject_name)
        await self.cursor.execute(f"""SELECT name, level, classes, site, state, profile FROM Olympiads
                                    WHERE subject_id = '{subject_id}'""")
        d = {}  # группиорока по уровню
        for olymp in await self.cursor.fetchall():
            name, level, classes, site, state, profile = olymp
            if await check_class(user_class, classes):  # добавляем только олимпиады, подходящие по классу
                if level not in d:
                    d[level] = []
                d[level].append((name, site, state, profile))
        ans = {}
        if len(d.keys()):
            for key in sorted(d):
                ans[key] = ''
                ans[key] += f"{key} уровень:\n"
                for elem in d[key]:
                    name, site, state, profile = elem
                    ans[key] += f"[{name}]({site}) \n"
                    ans[key] += f"Профиль: {profile}\n" 
                    ans[key] += f"Состояние: {state}\n\n"
        return ans

    # Пользователи
    # проверка существования пользователя
    async def user_exists(self, user_id):
        await self.cursor.execute(f"""SELECT * FROM Users WHERE Users.user_id = '{user_id}'""")
        result = await self.cursor.fetchone()
        return result

    # добавление пользователя (пока только chat_id)
    async def add_user_id(self, user_id, username):
        # conn = await asyncpg.connect(user=get_from_env('user'), password=get_from_env('password'), database=get_from_env('database'), host=get_from_env('host')) 
        await self.cursor.execute(f"""INSERT INTO users (user_id) VALUES('{user_id}');""")
        await self.cursor.execute(f"""UPDATE users SET username = '{username}' WHERE user_id = '{user_id}';""")
        await self.connection.commit()
        # await conn.close()

    # удаление пользователя
    async def delete_user(self, user_id):
        await self.cursor.execute(f"""DELETE FROM Users WHERE user_id = '{user_id}'""")
        await self.connection.commit()
    
    # добавление класса
    async def add_class(self, user_id, cl):
        await self.cursor.execute(f"""UPDATE users SET class = '{cl}' WHERE user_id = '{user_id}';""")
        await self.connection.commit()


    # геттеры
    # получение всех пользователей (для рассылки)
    # только id
    async def get_all_users(self):
        await self.cursor.execute("SELECT user_id FROM Users;")
        result = await self.cursor.fetchall()
        return result
    
    # вся информация
    async def get_all_users_info(self):
        await self.cursor.execute("SELECT * FROM Users;")
        result = await self.cursor.fetchall()
        return result
    
    # окончившие регистрация
    async def get_users_ended_registration(self):
        await self.cursor.execute("SELECT user_id FROM Users WHERE registration_status IS TRUE;")
        result = await self.cursor.fetchall()
        return result
    
    # неокончившие регистрация
    async def get_users_not_ended_registration(self):
        await self.cursor.execute("SELECT user_id FROM Users WHERE registration_status IS False;")
        result = await self.cursor.fetchall()
        return result
    
    # Устанавливаем статус учителя пользователю
    async def add_status_to_teacher(self, user_id, status):
        await self.cursor.execute(f"""UPDATE users SET teacher_status = '{status}' WHERE user_id = '{user_id}';""")
        await self.connection.commit()

    # Возвращаем bool значения статуса учителя
    async def check_teacher_status(self, user_id):
        await self.cursor.execute(f"""SELECT teacher_status FROM Users WHERE user_id = {user_id}""")
        result = await self.cursor.fetchone()
        res = result[0]
        return res
    
    # Устанавливаем флаг, когда учитель выбирает 8-11 класс, чтобы попасть в нужный обработчик
    async def change_flag_teachers_searching(self, user_id, status):
        await self.cursor.execute(f"""UPDATE users SET flag_teacher_search_class = '{status}' WHERE user_id = '{user_id}';""")
        await self.connection.commit()

    # Возвращаем bool значение флага, когда учитель выбирает 8-11 класс    
    async def check_flag_teachers_searching(self, user_id):
        await self.cursor.execute(f"""SELECT flag_teacher_search_class FROM Users WHERE user_id = {user_id}""")
        result = await self.cursor.fetchone()
        res = result[0]
        return res

    # получение класса пользователя ???
    async def get_class(self, user_id, cl):
        await self.cursor.execute(f"""SELECT class FROM Users WHERE Users.user_id = '{user_id}'""")
        res = await self.cursor.fetchone()
        result = res[0]
        if res is None:
            return False
        teacher_status = await self.check_teacher_status(user_id)
        if teacher_status:
            result = "Учитель"
        return result == cl

    
    # включена/выключена рассылка олимпиад
    async def get_mailing_olympiads_state(self, user_id):
        await self.cursor.execute(f"""SELECT mailing_olympiads FROM Users WHERE Users.user_id = '{user_id}'""")
        result = await self.cursor.fetchone()
        # ???
        if result is None:
            return None
        return result[0]

    # включена/выключена рассылка программирование
    async def get_mailing_status_of_programming(self, user_id):
        await self.cursor.execute(f"""SELECT mailing_programming FROM Users WHERE Users.user_id = '{user_id}'""")
        result = await self.cursor.fetchone()
        return result[0]
    
    # включена/выключена рассылка хакатонов
    async def get_mailing_hackathons_state(self, user_id):
        await self.cursor.execute(f"""SELECT mailing_hackathons FROM Users WHERE Users.user_id = '{user_id}'""")
        result = await self.cursor.fetchone()
        print(result)
        if result is None:
            return result
        return result[0]
    
    # окончил ли пользователь регистрацию
    async def get_user_registration_status(self, user_id):
        await self.cursor.execute(f"""SELECT registration_status FROM Users WHERE Users.user_id = '{user_id}'""")
        result = await self.cursor.fetchone()
        print("user_registration_status", result)
        return result[0]
    
    # получение класса пользователя ??? 
    async def get_user_class(self, user_id):
        await self.cursor.execute(f"""SELECT class FROM Users WHERE Users.user_id = '{user_id}'""")
        result = await self.cursor.fetchone()
        return result[0]
    
    async def del_user_class(self, user_id):
        await self.cursor.execute(f"""UPDATE users SET class = NULL WHERE user_id = '{user_id}';""")
        await self.connection.commit()
    
    # получение списка из названий предметов пользователя
    async def get_users_subjects_names(self, user_id):
        await self.cursor.execute(f"""SELECT subs FROM Users WHERE Users.user_id = '{user_id}'""")
        subjs = await self.cursor.fetchall()
        try:
            subjs = subjs[0][0].split(', ')
        except Exception:
            subjs = []
        ans = []
        for el in subjs:
            ans.append(await self.get_subjects_names_from_id(int(el)))
        return ans
    
    # работа с предметами
    async def add_del_sub(self, user_id, sub):
        await self.cursor.execute(f"""SELECT subs FROM Users WHERE Users.user_id = '{user_id}'""")
        subs = await self.cursor.fetchall()
        print("before add_del_sub", subs)
        if subs is None or subs[0] is None or subs[0][0] is None:
            result = False
        else:
            subs = subs[0][0].split(', ')
            print("add_del_sub", subs)
            # проверяем наличие предмета в бд (True - выбран, False - не выбран)
            result = True if str(sub) in str(subs) else False
        if result:
            # если за пользователем числится только один предмет, то меняем значение выбранных на NULL
            print("delete subject", subs)
            # if len(subs[0]) < 6:
            if len(subs) == 1:
                await self.cursor.execute(f"""UPDATE users SET subs = NULL WHERE user_id = '{user_id}';""")
            else:
                # из всех предметов из базы удаляем выбранное и добавляем всё назад
                print("remove", subs, sub)
                # subs = subs[0].split(', ')
                subs.remove(str(sub))
                add_str_subs = ', '.join(subs)
                await self.cursor.execute(f"""UPDATE users SET subs = '{add_str_subs}' WHERE user_id = '{user_id}';""")
            await self.connection.commit()
        else:
            nums = await self.count_subs(user_id)
            print("nums", nums)
            if nums < 5:
                # если за пользователем не числится предметов, то добавляем его первый предмет
                if subs[0][0] == None:
                    await self.cursor.execute(f"""UPDATE users SET subs = '{sub}' WHERE user_id = '{user_id}';""")
                    await self.connection.commit()
                else:
                    # ко всем предметам добавляем выбарнный и загружаем в бд
                    print("subs add_del_sub", subs)
                    subs.append(str(sub))
                    add_str_subs = ', '.join(subs)
                    await self.cursor.execute(f"""UPDATE users SET subs = '{add_str_subs}' WHERE user_id = '{user_id}';""")
                    await self.connection.commit() 
            else:
                # telegram просит обязательно обновить текст сообщения
                print(">6")
                return False
        return True
                
    # функция нужна для отображения галочек у выбранных предметов
    async def get_sub(self, user_id, sub):
        print(".......get_sub", user_id, sub)
        await self.cursor.execute(f"""SELECT subs FROM Users WHERE Users.user_id = '{user_id}'""")
        try:
            subjs = await self.cursor.fetchall()
            print("------>", subjs)
            sub_id = await self.get_subjects_id(sub)
            str_subjs = subjs[0][0].split(', ')
            # subjs = subjs.split(', ')
            flag = True if str(sub_id) in str_subjs else False
        except Exception as e:
            print("error", e)
            return False
        return flag
    
    # для отображения галочек у выбранных дней напоминаний
    async def get_remind_day(self, user_id, remind_day):
        await self.cursor.execute(f"""SELECT remind FROM Users WHERE user_id = '{user_id}'""")
        try:
            days = await self.cursor.fetchall()
            # print("->>>>", remind_day, days)
            return remind_day in days[0][0].split()
        except Exception as e:
            print("error", e)
            return False
    
    async def get_user_remind_days(self, user_id):
        await self.cursor.execute(f"""SELECT remind FROM Users WHERE user_id = '{user_id}'""")
        days = await self.cursor.fetchall()

        return days
    
    async def update_user_remind_days(self, user_id, str_days):
        await self.cursor.execute(f"""UPDATE Users SET remind = '{str_days}' WHERE user_id = '{user_id}'""")
        await self.connection.commit()
    
    # получаем класс для отображения в конце регистрации/при изменении класса
    async def get_class_for_registration_is_done(self, user_id):
        await self.cursor.execute(f"""SELECT class FROM Users WHERE Users.user_id = '{user_id}'""")
        cl = await self.cursor.fetchall()
        print("get_class_for_registration_is_done", cl)
        return cl[0][0]
    
    # получаем предметы для отображения в конце регистрации/при изменении класса
    async def get_subs_for_registration_is_done(self, user_id):
        await self.cursor.execute(f"""SELECT subs FROM Users WHERE Users.user_id = '{user_id}'""")
        subjs = await self.cursor.fetchall()
        print("get_subs_for_registration_is_done", subjs)
        if subjs is None or subjs[0] is None or subjs[0][0] is None:
            add_subs = "нет"
        else:
            subjs = subjs[0][0]
            subjs = subjs.split(', ')
            subs_in_str = []
            for i in subjs:
                subs_in_str.append(await self.get_subjects_names_from_id(int(i)))
            add_subs = ', '.join(subs_in_str)
        return add_subs
    
    # если пользователь выбирает класс "Не школьник", то отчищаем его предметы
    async def reset_subs_for_not_schoolboy(self, user_id):
        await self.cursor.execute(f"UPDATE users SET subs = NULL WHERE user_id = {user_id};")
        await self.connection.commit()
        
    # удаление пользователя
    async def delete_user(self, user_id):
        await self.cursor.execute(f"""DELETE FROM Users WHERE user_id = {user_id};""")
        await self.connection.commit()

    # окончание регистрации
    async def end_user_registration(self, user_id):
        await self.cursor.execute(f"""UPDATE Users SET registration_status = 'True' WHERE user_id = '{user_id}'""")
        await self.connection.commit()
    
    # обновление рассылки олимпиад (включить/выключить)
    async def update_user_mailing_olympiads(self, user_id, new_state_olympiads):
        await self.cursor.execute(f"""UPDATE Users SET mailing_olympiads = '{new_state_olympiads}' WHERE user_id = {user_id}""")
        await self.connection.commit()
    
    # обновление рассылки программирование (включить/выключить)
    async def update_user_mailing_programming(self, user_id, new_state_programming):
        await self.cursor.execute(f"""UPDATE Users SET mailing_programming = '{new_state_programming}' WHERE user_id = {user_id}""")
        await self.connection.commit()
        
    # обновление рассылки хакатонов (включить/выключить)
    async def update_user_mailing_hackathons(self, user_id, new_state_hackathons):
        await self.cursor.execute(f"""UPDATE Users SET mailing_hackathons = '{new_state_hackathons}' WHERE user_id = {user_id}""")
        await self.connection.commit()
    
    # Хакатоны
    # добавление информации о хакатоне
    async def add_hackathon(self, lenth, *args):
        await self.cursor.execute(f"""DELETE FROM hacks;""")
        try:
            for i in range(lenth):
                await self.cursor.execute(f"""INSERT INTO hacks (name, place, link, date, registr) 
                                    values('{args[0][i]['name']}',
                                    '{args[0][i]['place']}',
                                    '{args[0][i]['link']}',
                                    '{args[0][i]['Хакатон']}', 
                                    '{args[0][i]['Регистрация']}')""")
                keys = list(args[0][i].keys())
                if 'Технологический фокус' in keys:
                    await self.cursor.execute(f"""UPDATE hacks 
                                SET stack = '{args[0][i]['Технологический фокус']}'
                                WHERE name = '{args[0][i]['name']}'""")
                if 'Целевая аудитория' in keys:
                    await self.cursor.execute(f"""UPDATE hacks 
                                SET auditorium = '{args[0][i]['Целевая аудитория']}'
                                WHERE name = '{args[0][i]['name']}'""")
                if 'Призовой фонд' in keys:
                    await self.cursor.execute(f"""UPDATE hacks 
                                SET money = '{args[0][i]['Призовой фонд']}'
                                WHERE name = '{args[0][i]['name']}'""")
                if 'Организаторы' in keys:
                    await self.cursor.execute(f"""UPDATE hacks 
                                SET org = '{args[0][i]['Организаторы']}'
                                WHERE name = '{args[0][i]['name']}'""")
                if 'Организатор' in keys:
                    await self.cursor.execute(f"""UPDATE hacks 
                                SET org = '{args[0][i]['Организатор']}'
                                WHERE name = '{args[0][i]['name']}'""")
                await self.connection.commit()
        except Exception as ex:
            print(ex, i)
    
    # забираем хакатоны из бд
    async def take_hackathons_names(self):
        await self.cursor.execute("SELECT name FROM hacks")
        rows = await self.cursor.fetchall()
        names = [i[0] for i in rows]
        return names

    # список хакатонов
    async def take_hackathons(self):
        await self.cursor.execute("SELECT * FROM hacks;")
        messages = []
        result = await self.cursor.fetchall()
        for row in result:
            print("row", row)
            _, name, place, date, registr, stack, auditorium, money, org, link = row
            message = f"[{name}]({link}) \n"
            if place:
                message += f"Место проведения: {place} \n"
            if date:
                message += f"Дата проведения: {date} \n"
            if registr:
                message += f"Дата регистрации: {registr} \n"
            if stack:
                message += f"Технологический фокус: {stack} \n"
            if auditorium:
                message += f"Целевая аудитория: {auditorium} \n"
            if money:
                message += f"Приз: {money} \n"
            if org:
                message += f"Организатор(ы): {org} \n"
            messages.append(message)
        return messages
    
    # лагеря
    # проверка на существование
    async def camp_exists(self, name):
        await self.cursor.execute(f"""SELECT * FROM Camps WHERE name = '{name}'""")
        result = await self.cursor.fetchone()
        return result
    
    # добавление лагеря
    # название; классы; предметы; организаторы; состояние; ссылка на activity
    async def add_camp(self, name, classes, subjects, site, state, link):
        await self.cursor.execute(f"""INSERT INTO Camps (name, class, subjects, site, state, link)
                                VALUES('{name}', '{classes}', '{subjects}', '{site}', '{state}', '{link}')""")
        await self.connection.commit()

    # список всех школ
    async def get_all_camps(self):
        await self.cursor.execute("""SELECT * FROM Camps;""")
        result = await self.cursor.fetchall()
        return result
    
    # текущее состояние
    async def get_camp_state(self, name):
        await self.cursor.execute(f"""SELECT state FROM Camps WHERE name = '{name}';""")
        result = await self.cursor.fetchone()
        return result[0]
    
    # обновление состояние
    async def update_camp_state(self, name, state):
        await self.cursor.execute(f"""UPDATE Camps SET state = '{state}' WHERE name = '{name}'""")
        await self.connection.commit()

    # codeforces раунды. 
    # заметки: 1 - раунды сравниваем по дате и времени (не по названию)
    #          2 - в mailing идут только новые раунды
    # все текущие раунды из бд
    async def get_all_codeforces_rounds(self):
        await self.cursor.execute("""SELECT * FROM Contests WHERE platform = 'Codeforces';""")
        result = await self.cursor.fetchall()
        return result
    
    # новое состояние регистрации
    async def set_codeforces_round_registration_state(self, date_time, registration_state):
        await self.cursor.execute(f"""UPDATE Contests SET registration_state = '{registration_state}' WHERE platform = 'Codeforces' AND date_time = '{date_time}'""")
        await self.connection.commit()

    # добавляем новый раунд
    async def add_codeforces_round(self, name, date_time, registration_state):
        await self.cursor.execute(f"""INSERT INTO Contests (platform, name, date_time, registration_state)
                                VALUES('Codeforces', '{name}', '{date_time}', '{registration_state}')""")
        await self.connection.commit()

    # удаляем раунд (он уже прошёл)
    async def delete_codeforces_round(self, date_time):
        await self.cursor.execute(f"""DELETE FROM Contests WHERE platform = 'Codeforces' AND date_time = '{date_time}'""")
        await self.connection.commit()

    # codechef раунды.
    # все текущие codechef-раунды из бд
    async def get_all_codechef_rounds(self):
        await self.cursor.execute("""SELECT name, date_time, registration_state FROM Contests WHERE platform = 'CodeChef';""")
        result = await self.cursor.fetchall()
        return result

    # новое состояние регистрации
    async def set_codechef_round_registration_state(self, date_time, registration_state):
        await self.cursor.execute(f"""UPDATE Contests SET registration_state = '{registration_state}' WHERE platform = 'CodeChef' AND date_time = '{date_time}'""")
        await self.connection.commit()

    # добавляем новый раунд
    async def add_codechef_round(self, name, date_time, registration_state):
        await self.cursor.execute(f"""INSERT INTO Contests (platform, name, date_time, registration_state)
                                VALUES('CodeChef', '{name}', '{date_time}', '{registration_state}')""")
        await self.connection.commit()

    # удаляем раунд (он уже прошёл)
    async def delete_codechef_round(self, date_time):
        await self.cursor.execute(f"""DELETE FROM Contests WHERE platform = 'CodeChef' AND date_time = '{date_time}'""")
        await self.connection.commit()
    
    # LeetCode раунды
    # все текущие codechef-раунды из бд
    async def get_all_leetcode_rounds(self):
        await self.cursor.execute("""SELECT name, date_time, registration_state FROM Contests WHERE platform = 'LeetCode';""")
        result = await self.cursor.fetchall()
        return result
    
    # обновляем 
    async def set_leetcode_round_registration_state(self, name, date_time, registration_state, template_name):
        await self.cursor.execute(f"""UPDATE Contests 
                                  SET name = '{name}', date_time = '{date_time}', registration_state = '{registration_state}' 
                                  WHERE platform = 'LeetCode' AND name LIKE '%{template_name}%'""")
        await self.connection.commit()
        
    # забаненные
    # бан
    async def ban_user(self, chat_id, reason):
        await self.cursor.execute(f"""INSERT INTO Banned(user_id, reason)
                                VALUES('{chat_id}', '{reason}')""")
        await self.connection.commit()


    # убираем из списка забаненных
    async def unban_user(self, chat_id):
        await self.cursor.execute(f"""DELETE FROM Banned WHERE user_id = '{chat_id}'""")
        await self.connection.commit()

    # проверка
    async def check_ban(self, chat_id):
        await self.cursor.execute(f"""SELECT * FROM Banned WHERE user_id = '{chat_id}'""")
        result = await self.cursor.fetchall()
        return result
    
    # Для статистики по кол-во пользователей с вкл рассылкой по всем 3 столбцам
    async def get_true_count(self):
        await self.cursor.execute(f"""SELECT COUNT(*) FROM users WHERE mailing_olympiads = True AND registration_status = True;""")
        mail_oly = await self.cursor.fetchone()
        await self.cursor.execute(f"""SELECT COUNT(*) FROM users WHERE mailing_hackathons = True AND registration_status = True;""")
        mail_hack = await self.cursor.fetchone()
        await self.cursor.execute(f"""SELECT COUNT(*) FROM users WHERE mailing_programming = True AND registration_status = True;""")
        mail_prog = await self.cursor.fetchone()
        return mail_oly[0], mail_hack[0], mail_prog[0]

    # общие функции
    # вывод таблиц БД на экран
    def show_table(self, table_name):
        self.cursor.execute(f"""SELECT * FROM {table_name}""")
        pprint(self.cursor.fetchall())
        self.cursor.execute(f"""SELECT * FROM {table_name}""")
        print(len(self.cursor.fetchall()))
