import telebot
import sqlite3
from telebot import types
from datetime import datetime, timedelta

# Инициализация бота
TOKEN = '8095038946:AAF-j8fR2g1f_zkVlshE4eYvqIkgOFQUN10'
bot = telebot.TeleBot(TOKEN)

# Пример данных для хранения информации о мастерах и услугах
services = {
    'Мужская стрижка': ['Мастер 1', 'Мастер 2'],
    'Женская стрижка': ['Мастер 3', 'Мастер 4'],
    'Окрашивание': ['Мастер 5', 'Мастер 6']
}

# Словарь для хранения промежуточных данных о записи
user_appointments = {}
user_steps = {}  # Хранит текущий шаг пользователя


# Подключение к базе данных SQLite
def init_db():
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    # Создание таблицы users, если она не существует
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY, 
                        username TEXT, 
                        full_name TEXT)''')

    # Создание таблицы appointments, если она не существует
    cursor.execute('''CREATE TABLE IF NOT EXISTS appointments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        user_id INTEGER, 
                        service TEXT, 
                        master TEXT, 
                        date TEXT, 
                        time TEXT,
                        UNIQUE(user_id, date, time))''')

    conn.commit()
    conn.close()


# Добавление записи в базу данных
def add_appointment(user_id, service, master, date, time):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''INSERT INTO appointments (user_id, service, master, date, time) 
                          VALUES (?, ?, ?, ?, ?)''', (user_id, service, master, date, time))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        # Запись уже существует
        success = False

    conn.close()
    return success


# Получение списка записей для пользователя
def get_user_appointments(user_id):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    cursor.execute('''SELECT service, master, date, time FROM appointments WHERE user_id = ?''', (user_id,))
    appointments = cursor.fetchall()

    conn.close()
    return appointments


# Удаление записи
def delete_appointment(user_id, date, time):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    cursor.execute('''DELETE FROM appointments WHERE user_id = ? AND date = ? AND time = ?''', (user_id, date, time))
    conn.commit()
    conn.close()


# Главное меню
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Выбор услуги')
    btn2 = types.KeyboardButton('Отменить запись')
    btn3 = types.KeyboardButton('Просмотреть записи')
    btn4 = types.KeyboardButton('Контакты')
    btn5 = types.KeyboardButton('Помощь')
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup


# Приветственное сообщение для новых пользователей с запросом имени
@bot.message_handler(commands=['start'])
def welcome(message):
    user_id = message.chat.id
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    # Проверяем, есть ли пользователь в базе, если нет — добавляем
    cursor.execute('SELECT full_name FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()

    if user is None:
        # Запрашиваем у пользователя его имя
        msg = bot.send_message(user_id, "Добро пожаловать! Как вас зовут?")
        bot.register_next_step_handler(msg, save_user_name)
    else:
        full_name = user[0]
        bot.send_message(user_id, f"Добро пожаловать, {full_name}! Выбирайте услугу",
                         reply_markup=main_menu())

    conn.close()


# Сохранение имени пользователя и приветствие
def save_user_name(message):
    full_name = message.text
    user_id = message.chat.id

    # Сохраняем имя пользователя в базу данных
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    cursor.execute('''INSERT OR REPLACE INTO users (user_id, username, full_name) 
                      VALUES (?, ?, ?)''', (user_id, message.from_user.username, full_name))
    conn.commit()
    conn.close()

    # Приветственное сообщение
    bot.send_message(user_id, f"Приятно познакомиться, {full_name}! Выбирайте услугу",
                     reply_markup=main_menu())


# Запись на стрижку
@bot.message_handler(func=lambda message: message.text == 'Выбор услуги')
def book_appointment(message):
    user_appointments[message.chat.id] = {}
    user_steps[message.chat.id] = 'service'  # Устанавливаем шаг

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for service in services.keys():
        markup.add(types.KeyboardButton(service))

    # Добавляем кнопку возврата
    markup.add(types.KeyboardButton('Назад'))

    bot.send_message(message.chat.id, "Выберите услугу:", reply_markup=markup)
    bot.register_next_step_handler(message, select_master)


# Обработчик выбора мастера
def select_master(message):
    if message.text == 'Назад':
        bot.send_message(message.chat.id, "Выберите услугу:", reply_markup=main_menu())
        return

    user_appointments[message.chat.id]['service'] = message.text
    user_steps[message.chat.id] = 'master'  # Устанавливаем шаг

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    selected_service = message.text
    for master in services[selected_service]:
        markup.add(types.KeyboardButton(master))

    # Добавляем кнопку возврата
    markup.add(types.KeyboardButton('Назад'))

    bot.send_message(message.chat.id, "Выберите мастера:", reply_markup=markup)
    bot.register_next_step_handler(message, select_date)


# Обработчик выбора даты
def select_date(message):
    if message.text == 'Назад':
        if user_steps.get(message.chat.id) == 'master':
            return book_appointment(message)  # Возврат к выбору услуги
        elif user_steps.get(message.chat.id) == 'service':
            bot.send_message(message.chat.id, "Выбор услуги отменен.", reply_markup=main_menu())
            return

    user_appointments[message.chat.id]['master'] = message.text
    selected_master = message.text
    user_steps[message.chat.id] = 'date'  # Устанавливаем шаг

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    today = datetime.now().date()

    # Доступные даты для записи - на 30 дней вперед
    dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]

    for date in dates:
        markup.add(types.KeyboardButton(date))

    # Добавляем кнопку возврата
    markup.add(types.KeyboardButton('Назад'))

    bot.send_message(message.chat.id, f"Выберите дату для мастера {selected_master}:", reply_markup=markup)
    bot.register_next_step_handler(message, select_time)


# Обработчик выбора времени
def select_time(message):
    if message.text == 'Назад':
        if user_steps.get(message.chat.id) == 'date':
            return select_date(message)  # Возврат к выбору даты
        elif user_steps.get(message.chat.id) == 'master':
            return select_master(message)  # Возврат к выбору мастера
        elif user_steps.get(message.chat.id) == 'service':
            return book_appointment(message)  # Возврат к выбору услуги
        elif user_steps.get(message.chat.id) == 'time':
            # Проверяем, установлен ли мастер
            if 'master' in user_appointments[message.chat.id]:
                return select_master(message)  # Возврат к выбору мастера
            else:
                bot.send_message(message.chat.id,
                                 "Ошибка: Мастер не выбран. Пожалуйста, выберите услугу и мастера заново.",
                                 reply_markup=main_menu())
                return

    user_appointments[message.chat.id]['date'] = message.text
    selected_date = message.text
    selected_master = user_appointments[message.chat.id]['master']
    user_steps[message.chat.id] = 'time'  # Устанавливаем шаг

    # Получаем текущее время
    now = datetime.now()

    # Доступное время для записи (например, с 10:00 до 18:00 с шагом в час)
    available_times = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00']

    # Если выбрана текущая дата, исключаем прошедшие временные слоты
    if selected_date == now.strftime('%Y-%m-%d'):
        available_times = [time for time in available_times if time > now.strftime('%H:%M')]

    # Проверяем занятые временные слоты
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    cursor.execute('SELECT time FROM appointments WHERE date = ? AND master = ?', (selected_date, selected_master))
    booked_times = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Исключаем занятые временные слоты
    free_times = [time for time in available_times if time not in booked_times]

    # Проверяем, есть ли свободное время
    if free_times:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for time in free_times:
            markup.add(types.KeyboardButton(time))

        # Добавляем кнопку возврата
        markup.add(types.KeyboardButton('Назад'))

        bot.send_message(message.chat.id, f"Выберите время для {selected_master} на {selected_date}:",
                         reply_markup=markup)
        bot.register_next_step_handler(message, confirm_appointment)
    else:
        bot.send_message(message.chat.id,
                         "К сожалению, на выбранную дату и мастера нет доступного времени. Пожалуйста, выберите другую дату или мастера.",
                         reply_markup=main_menu())


# Подтверждение записи
def confirm_appointment(message):
    if message.text == 'Назад':
        return select_time(message)  # Возврат к выбору времени

    selected_time = message.text
    user_id = message.chat.id

    # Добавляем запись в базу данных
    success = add_appointment(user_id, user_appointments[user_id]['service'],
                              user_appointments[user_id]['master'],
                              user_appointments[user_id]['date'], selected_time)

    if success:
        bot.send_message(user_id, "Запись успешно добавлена!", reply_markup=main_menu())
    else:
        bot.send_message(user_id, "Ошибка: Запись на это время уже существует.", reply_markup=main_menu())


# Отмена записи
@bot.message_handler(func=lambda message: message.text == 'Отменить запись')
def cancel_appointment(message):
    user_id = message.chat.id
    appointments = get_user_appointments(user_id)

    if not appointments:
        bot.send_message(user_id, "У вас нет записей.", reply_markup=main_menu())
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for appointment in appointments:
        service, master, date, time = appointment
        markup.add(types.KeyboardButton(f"{service} - {master} на {date} в {time}"))

    markup.add(types.KeyboardButton('Назад'))

    bot.send_message(user_id, "Выберите запись для отмены:", reply_markup=markup)
    bot.register_next_step_handler(message, process_cancellation)


# Обработка отмены записи
def process_cancellation(message):
    if message.text == 'Назад':
        bot.send_message(message.chat.id, "Выбор отмены записи отменен.", reply_markup=main_menu())
        return

    user_id = message.chat.id
    selected_appointment = message.text

    # Проверка корректности формата
    if " - " in selected_appointment and " на " in selected_appointment and " в " in selected_appointment:
        try:
            service_master, date_time = selected_appointment.split(" на ")
            service, master = service_master.split(" - ")
            date, time = date_time.split(" в ")
            delete_appointment(user_id, date, time)
            bot.send_message(user_id, "Запись успешно отменена.", reply_markup=main_menu())
        except ValueError:
            bot.send_message(user_id, "Ошибка: Не удалось отменить запись. Пожалуйста, попробуйте еще раз.",
                             reply_markup=main_menu())
    else:
        bot.send_message(user_id, "Ошибка: Неверный формат записи. Пожалуйста, попробуйте снова.",
                         reply_markup=main_menu())


# Просмотр записей
@bot.message_handler(func=lambda message: message.text == 'Просмотреть записи')
def view_appointments(message):
    user_id = message.chat.id
    appointments = get_user_appointments(user_id)

    if not appointments:
        bot.send_message(user_id, "У вас нет записей.", reply_markup=main_menu())
        return

    response = "Ваши записи:\n"
    for appointment in appointments:
        service, master, date, time = appointment
        response += f"{service} - {master} на {date} в {time}\n"

    bot.send_message(user_id, response, reply_markup=main_menu())


# Инициализация базы данных
init_db()

# Запуск бота
bot.polling(none_stop=True)
