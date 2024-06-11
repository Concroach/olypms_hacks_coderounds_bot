# парсинг всех необходимых данных с https://olimpiada.ru/
from bs4 import BeautifulSoup
import requests
# import cfscrape
import asyncio
import aiohttp
import datetime
from db import Database

from find_date import get_dates, convert_to_datetime_date

# ссылки на страницы сайта, откуда парсятся данные
URL_SUBJECTS = "https://olimpiada.ru/article/1045"
URL_OLYMPIADS = "https://olimpiada.ru/article/1090"
URL_CAMPS = "https://olimpiada.ru/activities?vs=on&class=any&type=any&period_date=&period=year"


d = {
    "Jan": "января",
    "Feb": "февраля",
    "Mar": "марта",
    "Apr": "апреля",
    "May": "мая",
    "Jun": "июня",
    "Jul": "июля",
    "Aug": "августа",
    "Sep": "сентября",
    "Oct": "октября",
    "Nov": "ноября",
    "Dec": "декабря"
}


d_number = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12
}




# парсинг списка предметов - 
# запускатеся вручную, поэтому не async
def parse_all_subjects(db):
    url = URL_SUBJECTS
    page = requests.get(url)
    flag_subjects = False
    if not page:
        print(page.status_code, page.reason)
        flag_subjects = page.status_code
        return
    soup = BeautifulSoup(page.text, "lxml")
    html_subjects = soup.find("table", class_="note_table")  # таблица с названиями предметов (html-строки)
    subjects_names = []  # сами названия и их id(для дальнейшего поиска)
    for elem in html_subjects.findAll("a"):
        subjects_names.append((elem.text, elem.get("href")[1:]))
    for elem in subjects_names:
        name, html_name = elem
        # если предмета нет - добавляем его
        if not db.subjects_exists(name):
            db.add_subject(name, html_name)
            flag_subjects = True  
    return flag_subjects


# тоже нет в коде
async def parse_subject(subject_name, subject_id, db):
    url = URL_OLYMPIADS
    page = requests.get(url)
    if not page:
        print(page.status_code, page.reason)
        return
    soup = BeautifulSoup(page.text, "lxml")
    ref = soup.select("a#" + subject_id)[0]  # нужный заголок
    table = ref.find_next("table", class_="note_table")  # Нужная таблица
    # данные из таблицы (название, номер из перечня, профиль, предмет, уровень)
    data = []
    for line in table.find_all("tr"):
        data.append([])
        for value in line.find_all("td"):
            data[-1].append(value.text.strip())
        # на отдельной странице олимпиады ищем классы участия и ссылку на сайт
        link = line.findAll("a", class_="slim_dec",href=True)
        if not len(link):
            data[-1].append("Класс")
            data[-1].append("Ссылка на сайт")
            data[-1].append("Состояние")
            data[-1].append("Ссылка на страницу")
            continue
        href_value = link[0].get("href")
        olymp_url = "https://olimpiada.ru" + href_value
        olymp_page = requests.get(olymp_url)
        if not olymp_page:
            print(olymp_page.status_code, olymp_page.reason)
            continue
        soup_olymp = BeautifulSoup(olymp_page.text, "lxml")
        # классы участия
        try:
            classes = soup_olymp.find("span", class_="classes_types_a").text
        except Exception:
            del data[-1]
            continue
        data[-1].append(classes.strip())
        # ссылка на сайт
        all_contacts = soup_olymp.findAll("span", class_="bold timetableH2")
        for contact in all_contacts:
            if contact.text == "Контакты":
                site = contact.find_next("a", class_="color").get("href")
                data[-1].append(site.strip())
        # состояние
        state = soup_olymp.find("a", class_="red").text
        state = state.strip()
        data[-1].append(state[:(len(state) - 2)])
        # ссылка на страницу олимпиады, чтобы получать обновления
        data[-1].append(olymp_url)
    # группируем олимпиады из одного раздела по номеру в перечне
    d = {}
    for elem in data:
        name, number, profile, subject, level, olymp_classes, site, state, link = elem
        if number not in d:
            d[number] = [name, number, profile, subject, level, olymp_classes, site, state, link]
        else:
            d[number][2] += ', ' + profile  # добавляем профиль
            if subject not in d[number][3]:
                d[number][3] += ', ' + subject
    # переносим словарь в массив
    grouped_data = []
    for _, val in d.items():
        grouped_data.append(val)
    # обрабатываем профили и предметы. Если строка получается слишком длинной, меняем её на более общую фразу
    for elem in grouped_data:
        if len(elem[2]) > 30:  # профилей много -> Многопрофильная
            elem[2] = "Многопрофильная"
        elem[3] = subject_name
    print(grouped_data)
    all_olympiads = await db.get_all_olympiads_of_certain_subjects(subject_name)
    for elem in grouped_data[1:]:
        if await db.olympiad_exists(elem[0], elem[3]) is None:
            await db.add_olympiad(*elem)  # добавляем олимпиаду (проверка выше)
        else:
            print(elem[0], elem[3], elem[8])
            await db.update_olympiad_link(elem[0], elem[3], elem[8])  # навзание, название предмета, ссылка


# получаем id олимпиад с новым статусом
async def get_olympiads_updates(subject_name, db):
    print("here")
    all_olympiads = await db.get_all_olympiads_of_certain_subjects(subject_name)
    print("get_olympiads_updates", all_olympiads)
    data = []
    async with aiohttp.ClientSession() as session:
        for olymp in all_olympiads:
            print(olymp)
            url = olymp[-1]
            olymp_page = await session.get(url, ssl=False)
            if not olymp_page:
                print(olymp_page.status_code, olymp_page.reason)
                continue
            data.append([olymp[0]])  # имя олимпиады
            soup_olymp = BeautifulSoup(await olymp_page.text(encoding="utf8"), "lxml")
            # классы участия
            try:
                classes = soup_olymp.find("span", class_="classes_types_a").text
            except Exception:
                del data[-1]
                continue
            data[-1].append(classes.strip())
            # ссылка на сайт
            all_contacts = soup_olymp.findAll("span", class_="bold timetableH2")
            for contact in all_contacts:
                if contact.text == "Контакты":
                    site = contact.find_next("a", class_="color").get("href")
                    data[-1].append(site.strip())
            # состояние
            state = soup_olymp.find("a", class_="red").text
            state = state.strip()
            data[-1].append(state[:(len(state) - 2)])
            # ссылка на страницу олимпиады, чтобы получать обновления
            data[-1].append(url)
            
    news = {
        "new": [],
        "remind": {
            "1": [],
            "3": [],
            "7": [],
            "14": []
        }
    }
    for elem in data:
        name, classes, site, state, link = elem
        await db.update_olympiad_site(name, subject_name, site)
        await db.update_olympiad_classes(name, subject_name, classes)
        print(state, db.get_olympiad_state(name, subject_name))
        if state != await db.get_olympiad_state(name, subject_name):
            await db.update_olympiad_state(name, subject_name, state)
            news["new"].append(await db.get_olympiad_id(name, subject_name))
        else:
            today_date = datetime.date.today()
            text_dates = get_dates(state)
            for part in text_dates:
                flag_end = False  # чтобы не доблять одно и то же событие несколько раз
                for date in part:
                    datetime_date = convert_to_datetime_date(date[0], date[1])
                    days_delta = (datetime_date - today_date).days
                    if days_delta in [1, 3, 7, 14]:
                        news["remind"][str(days_delta)].append(await db.get_olympiad_id(name, subject_name))
                        flag_end = True
                        break
                if flag_end:
                    break

    return news


# списки летних лагерей
async def parse_camps(db):
    url = URL_CAMPS
    page = requests.get(url)
    # страница с лагерями
    if not page.text:
        return
    soup = BeautifulSoup(page.text, "lxml")
    news = {
        "new": [],
        "remind": []
    }
    
    # каждый лагерь
    async with aiohttp.ClientSession() as session:
        for elem in soup.find_all("div", class_="o-block"):
            link = elem.findAll("a", class_="none_a black olimp_desc",href=True)
            href_value = link[0].get("href")
            camp_url = "https://olimpiada.ru" + href_value
            camp_page = await session.get(camp_url, ssl=False)
            if not camp_page:
                continue
            # достаем название, классы, предметы, контакты, состояние
            camp_soup = BeautifulSoup(await camp_page.text(encoding="utf8"), "lxml")
            name = camp_soup.find("h1").text  # название
            classes = camp_soup.find("span", class_="classes_types_a").text
            subjects = []
            subjects_frame = camp_soup.find("div", class_="subject_tags_full")
            for block in subjects_frame.find_all("span", class_="subject_tag small-tag"):
                if block.text.strip() == "Иностранный язык":
                    subjects.append("639")
                elif block.text.strip() == "Русский язык":
                    subjects.append("620")
                else:
                    try:
                        subjects.append(str(await db.get_subjects_id(block.text.strip())))
                    except Exception:
                        print(f"Subject {block.text.strip()} does not exists")
            for block in subjects_frame.find_all("span", class_="subject_tag"):
                if block.text.strip() == "Иностранный язык":
                    subjects.append("639")
                elif block.text.strip() == "Русский язык":
                    subjects.append("620")
                else:
                    try:
                        subjects.append(str(await db.get_subjects_id(block.text.strip())))
                    except Exception:
                        print(f"Subject {block.text.strip()} does not exists")
            str_subjects = ', '.join(subjects)
            site = ''
            all_contacts = camp_soup.findAll("span", class_="bold timetableH2")
            for contact in all_contacts:
                if contact.text == "Контакты":
                    site = contact.find_next("a", class_="color").get("href")
            
            try:
                prev_state = await db.get_camp_state(name)
                state = camp_soup.find("a", class_="red").text.strip()[:-2]
                if prev_state != state:
                    news["new"].append((name, classes, subjects, site, state))
                    await db.update_camp_state(name, state)
                else:
                    today_date = datetime.date.today()
                    text_dates = get_dates(state)
                    for part in text_dates:
                        flag_end = False  # чтобы не доблять одно и то же событие несколько раз
                        for date in part:
                            datetime_date = convert_to_datetime_date(date[0], date[1])
                            days_delta = (datetime_date - today_date).days
                            print("camp delta", days_delta)
                            if days_delta in [1, 3, 7, 14]:
                                news["remind"].append((name, classes, subjects, site, state))
                                flag_end = True
                                break
                        if flag_end:
                            break
            except Exception as e:
                state = 'Пока неизвестно'
                with open("parse_camps.txt", 'a') as file:
                    file.write(f"ERROR parse camp: {e}")

            print(name, classes, str_subjects, site, state, camp_url)
            # если лагерь новый - добавляем в бд
            does_exist = await db.camp_exists(name)
            if not does_exist:
                await db.add_camp(name, classes, str_subjects, site, state, camp_url)
    # для рассылки возвращаем id новых лагерей
    # curr_state = "Открыта предзапись на годовые бесплатные онлайн-кружки по олимпиадному программирования: http://nlogn.info/classes?utm_source=tg"
    # curr_state = curr_state.replace('_', '')
    # news += [("NlogN", "8–11 классы", ["642"], "https://t.me/s/nlogninfo", curr_state)]
    return news


# парсинг codeforces раундов. Обновляются статусы регистрации, добавляются/удаляются раунды
# возвращается список новых раундов (для расслыки)
async def parse_codeforces_rounds(db):
    url = "https://codeforces.com/contests"
    page = requests.get(url)
    if not page.text:
        print(page.status_code, page.description)
        return
    soup = BeautifulSoup(page.text, "lxml")
    current_contests = soup.find("div", class_="datatable")
    table = current_contests.find("table", class_="")
    all_contests = table.find_all("tr")
    all_codeforces = await db.get_all_codeforces_rounds()
    print(all_codeforces)
    mailing_list = []
    for elem in all_contests[1:]:
        # название
        name = elem.find("td").text.strip()

        # дата
        date_time_soup = elem.find("span", class_="format-time").text
        date, time = date_time_soup.split()
        month, day, year = date.split('/')
        date_time = f"{day} {d[month]} {year} {time}"

        # регистрация
        registration_ref_soup = elem.find("a", class_="red-link")
        registration_ref = ''
        if registration_ref_soup is None:  # регистрация ещё не началась
            today_date = datetime.date.today()
            contest_date = datetime.date(int(year), d_number[month], int(day))
            days = (contest_date - today_date).days
            registration_ref = f"Дней до начала: {days}"
            if int(days) in [1, 3, 7, 10]:
                mailing_list.append((name, date_time, registration_ref))
        else:
            full_reference = "https://codeforces.com" + registration_ref_soup.get("href")
            registration_ref = f"Регистрация: {full_reference}"

        
        flag_new = True
        for elem in all_codeforces:
            _, platform, cur_name, cur_time, cur_registration = elem
            if date_time == cur_time:
                # обновляем регисрацию
                await db.set_codeforces_round_registration_state(date_time, registration_ref)
                flag_new = False
                # убираем элемент из списка
                all_codeforces.remove(elem)
                break
        if flag_new:
            # добаляем в бд
            await db.add_codeforces_round(name, date_time, registration_ref)
    # удаляем из бд что осталось
    for elem in all_codeforces:
        # delete from db
        _, paltform, name, date_time, registration_state = elem
        await db.delete_codeforces_round(date_time)
        pass
    return mailing_list


async def parse_leetcode(db):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0'
    }
    url = 'https://leetcode.com/contest/'
    page = requests.get(url, headers=headers)
    soup = BeautifulSoup(page.text, "lxml")
    
    swiper_slide = soup.find_all('div', class_="swiper-slide")
    cnt = 0
    mailing_list = []
    for swiper in swiper_slide:
        if cnt < 2:
            a = swiper.find('a', class_='h-full')
            link_from_website = a.get('href')
            real_link = 'https://leetcode.com' + link_from_website
            
            name_from_website = swiper.find('div', class_='truncate')
            name = name_from_website.text
            
            current_date = datetime.datetime.now()

            nearest_sunday = current_date + datetime.timedelta(days=(6 - current_date.weekday()) % 7)

            nearest_saturday = nearest_sunday - datetime.timedelta(days=nearest_sunday.weekday() - 5) 
            if nearest_saturday.day not in range(1, 8) and nearest_saturday.day not in range(15, 22):
                nearest_saturday += datetime.timedelta(weeks=1)

            if current_date == nearest_saturday:
                nearest_saturday += datetime.timedelta(weeks=2)
            elif current_date > nearest_saturday:
                nearest_saturday += datetime.timedelta(weeks=2)

            delta_next = nearest_sunday - current_date
            delta_next_next = nearest_saturday - current_date
            
            formatted_date_weekly = nearest_sunday.strftime("%d.%m.%Y")
            formatted_date_biweekly = nearest_saturday.strftime("%d.%m.%Y")
            
            finally_date_for_weekly = f'5:30 {formatted_date_weekly}'
            finally_date_for_biweekly = f'17:30 {formatted_date_biweekly}'
            if 'Weekly' in name:
                await db.set_leetcode_round_registration_state(name, finally_date_for_weekly, real_link, "Weekly")
                if delta_next.days in [1, 3, 7, 10]:
                    mailing_list.append((name, finally_date_for_weekly, real_link))
            else:
                await db.set_leetcode_round_registration_state(name, finally_date_for_biweekly, real_link, "Biweekly")
                if delta_next_next.days in [1, 3, 7, 10]:
                    mailing_list.append((name, finally_date_for_biweekly, real_link))
            cnt += 1
    return mailing_list


# codechef-раунды (не прасинг, а запрос, возвращающий контесты в json-формате)
async def get_codechef_rounds(db):
    url = "https://www.codechef.com/api/list/contests/all?sort_by=START&sorting_order=asc&offset=0&mode=premium"
    response = requests.get(url)

    if not response:
        print(response.status_code, response.reason)
        return
    today = datetime.datetime.now()
    today_day = today.day
    today_month = today.month
    today_year = today.year
    today_date = datetime.date(year=today_year, month=today_month, day=today_day)

    mailing_list = []
    all_contests = await db.get_all_codechef_rounds()
    json_response = response.json()
    future_contests = json_response["future_contests"]
    for elem in future_contests:
        name = elem["contest_name"]
        date_time_all = elem["contest_start_date"]
        day, month, year, time = date_time_all.split()
        hours, minuts, seconds = time.split(':')
        month_rus = d[month]
        date_time = f"{day} {month_rus} {year} {hours}:{minuts}"
        cur_date = datetime.date(year=int(year), month=d_number[month], day=int(day))
        delta = cur_date - today_date
        print("delta", delta, type(delta))
        registration_state = f"Дней до начала контеста: {delta.days}"
        if str(delta).split()[0] == '0:00:00' or int(str(delta).split()[0]) in [1, 3, 7, 10]:
            mailing_list.append((name, date_time, registration_state))
        print(name, date_time, registration_state)

        flag_new = True
        for elem in all_contests:
            cur_name, cur_date_time, cur_registration = elem
            print(cur_date_time, date_time)
            if cur_date_time == date_time:
                print("set_registration")
                await db.set_codechef_round_registration_state(cur_date_time, registration_state)
                flag_new = False
                all_contests.remove(elem)
                break

        if flag_new:
            await db.add_codechef_round(name, date_time, registration_state)
    for elem in all_contests:
        name, date_time, reg = elem
        await db.delete_codechef_round(date_time)
    return mailing_list

