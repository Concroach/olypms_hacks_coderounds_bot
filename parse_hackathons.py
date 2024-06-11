"""Парсер акутальных хакатанов на https://www.хакатоны.рф/"""
import requests
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from db import Database


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0'
}

    # запрос
url = "https://www.хакатоны.рф/"
response = requests.get(url, headers=headers)

#     # сохраняем html
with open("page_content.html", "w", encoding="utf-8") as file:
    file.write(response.text)

   # открываем html
with open ('page_content.html', 'r', encoding="utf-8") as file:
    src = file.read()
    
    
    # находим все хакатоны // hackathons - список из html кода каждого хакатона
soup = BeautifulSoup(src, 'html.parser')
hackathons = soup.find_all('div', class_='t776__content')

info_hackathons = [] # список словарей с информацией о хакатонах
count_of_hackathons = 0 # число хакатонов

links = [] # список ссылок на хакатоны
for link in soup.find_all('a', {'class': 'js-product-link'}):
    links.append(link.get('href'))


for hackathon in hackathons:
    info_hackathons.append({})
    lines = [] # прочие параметры (дата, регистрация, тех. фокус,...)
    
    # название хакатона
    name_of_hack = hackathon.find('div', class_='t776__title').find('div')
    if name_of_hack:
        name = name_of_hack.text.replace("'", '`')
   
    # описание хакатона
    description = hackathon.find('div', class_='t776__descr')
    if description:
        for element in description:
            text = element.get_text(separator="\n")
            if text.strip():
                lines.append(text.strip())
    
    # место проведения
    place = lines[0]
    
    # добавляем в словарь название и место
    info_hackathons[count_of_hackathons].update({'name': name, 'place': place, 'link': links[count_of_hackathons]})
    
    # добавляем всю дргую инфу
    lines = lines[1:]
    lines = '\n'.join(lines)
    lines = lines.split('\n')
    lines = [t.strip() for t in lines if t.strip()]
    try:
        lines[lines.index('Редактировать:')] = 'Регистрация:'
    except:
        print(1)
    for i in range(0, len(lines) - 1, 2):
        key = lines[i].strip(':')
        value = lines[i + 1]
        info_hackathons[count_of_hackathons].update({key: value})
        
    count_of_hackathons += 1

necessary_hacks = [] # актуальные хакатоны
today = datetime.today().date()
current_year = datetime.now().year
info_hackathons = info_hackathons[:10] # делаем срез
for dictionary in info_hackathons:
    try:
        registration_date = dictionary["Регистрация"]
        registration_date = registration_date.replace("до", "").strip()
        month = {
            "января": 1,
            "февраля": 2,
            "марта": 3,
            "апреля": 4,
            "мая": 5,
            "июня": 6,
            "июля": 7,
            "августа": 8,
            "сентября": 9,
            "октября": 10,
            "ноября": 11,
            "декабря": 12
        }[registration_date.split()[1]]
        day = int(registration_date.split()[0])
        if month > 3:
            registration_date = datetime.today()
        else:
            registration_date = datetime(current_year, month, day - 2).date()
        if registration_date > today:
            necessary_hacks.append(dictionary)
    except:
        print(2)
        
db = Database()
# делаем проверку на появление новых хакатонов
async def check(db):
    old_names = await db.take_hackathons_names() # список названий хакатонов, которые уже в DB
    new_hacks = []
    for i in necessary_hacks:
        if i['name'] not in old_names:
            new_hacks.append(i)
    return new_hacks

# передаем данные в базу данных
async def add(db):
    await db.add_hackathon(len(necessary_hacks), necessary_hacks)
