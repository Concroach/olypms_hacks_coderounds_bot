import re
import datetime

months = [
    "январ",
    "феврал",
    "март",
    "апрел",
    "июн",
    "июл",
    "август",
    "сентябр",
    "октябр",
    "ноябр",
    "декабр",
    "май",
    "мая",
    "мае"
]

months_full = {
    "январ": "январь",
    "феврал": "февраль",
    "март": "март",
    "апрел": "апрель",
    "июн": "июнь",
    "июл": "июль",
    "август": "август",
    "сентябр": "сентябрь",
    "октябр": "октябрь",
    "ноябр": "ноябрь",
    "декабр": "декабрь",
    "май": "май",
    "мая": "май",
    "мае": "май"
}

months_number = {
    "январь": 1,
    "февраль": 2,
    "март": 3,
    "апрель": 4,
    "май": 5,
    "июнь": 6,
    "июль": 7,
    "август": 8,
    "сентябрь": 9,
    "октябрь": 10,
    "ноябрь": 11,
    "декабрь": 12
}

def check_month(word):
    for month in months:
        if word.startswith(month):
            return True

    return False

def check_bad_condition(word):

    return word.startswith("класс")

def check_is_digit(word):
    # допукаются случаи вида 13-15 
    for symb in word:
        if not(symb.isdigit() or symb == '-'):
            return False

    return True

def get_full_month(word):
    for month in months:
        if word.startswith(month):
            return months_full[month]
        
def convert_to_datetime_date(day, month):
    day = int(day)
    month = int(months_number[month])
    today_date = datetime.date.today()
    year = today_date.year

    # событие в следующем году
    if today_date.month > month:
        year += 1

    return datetime.date(year, month, day)

def get_dates(line):
    """
    Сначала разбиваем строку на 'смысловые' части (по запятой/точке/точке с запятой)
    Потом внутри 'предложений' находим даты.
    Идём слева направо, 
                        если встречаем месяц - запоманаем его
                        если встречаем слово типа "класс" - обнуляем месяц(потому что пойдут числа - классы - их не нужно запоминать)
                        встретили число (в том числе вида n-n) - добавляем в result пару (число, месяц)
    """
    result = []
    # следующая строка - разбиение по одному из раздилителей
    sentences = re.split(r'[.,;]', line)
    for sentence in sentences:
        result.append([])
        words = sentence.split()
        words.reverse()
        current_month = ""
        for word in words:
            word = word.lower()
            if check_month(word):
                current_month = get_full_month(word)
            if check_bad_condition(word):
                current_month = ""
            if check_is_digit(word):
                if current_month != "":
                    for number in word.split('-'):
                        result[-1].append((number, current_month))
        result[-1].reverse()

    return result

def test_get_dates():
    test_data = [
        "Теоретический тур финала пройдет 10 февраля",
        "Результаты отборочного этапа ожидаются 31 января",
        "Регистрация в финал будет открыта с 1 февраля по 1 марта, состязание состоится 3 марта",
        "Финал для 5-7 классов состоится 10 февраля",
        "Заключительный этап пройдет 23 и 30 марта",
        "Теоретический тур пройдет 17 февраля; регистрация открыта до 20:00 16 февраля",
        "Следующая олимпиада ожидается в январе 2024 года",
        "Идет подведение итогов отборочного этапа для 6-9 классов",
        'Идет подведение итогов отборочного этапа'
    ]
    today_date = datetime.date.today()
    for data in test_data:
        text_dates = get_dates(data)
        datetime_dates = []
        for part in text_dates:
            datetime_dates.append([])
            for date in part:
                datetime_dates[-1].append(convert_to_datetime_date(date[0], date[1]))
                print((datetime_dates[-1][-1] - today_date).days)
        print("------")
