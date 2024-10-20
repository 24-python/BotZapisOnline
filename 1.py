import telebot
import sqlite3
from telebot import types
from datetime import datetime, timedelta

# Инициализация бота
TOKEN = 'YOUR_TOKEN_HERE'
bot = telebot.TeleBot(TOKEN)

# Пример данных для хранения информации о мастерах и услугах
services = ['Мужская стрижка', 'Женская стрижка', 'Окрашивание']
masters = ['Вера', 'Надежда', 'Любовь']

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
    for service in services:
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
    for master in masters:
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
            return select_master(message)  # Возврат к выбору мастера
        elif user_steps.get(message.chat.id) == 'master':
            return book_appointment(message)  # Возврат к выбору услуги
        elif user_steps.get(message.chat.id) == 'service':
            bot.send_message(message.chat.id, "Выбор услуги отменен.", reply_markup=main_menu())
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

    # Получаем занятые временные слоты для выбранного мастера и даты
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
        if user_steps.get(message.chat.id) == 'time':
            return select_date(message)  # Возврат к выбору даты
        elif user_steps.get(message.chat.id) == 'date':
            return select_master(message)  # Возврат к выбору мастера
        elif user_steps.get(message.chat.id) == 'master':
            return book_appointment(message)  # Возврат к выбору услуги
        elif user_steps.get(message.chat.id) == 'service':
            bot.send_message(message.chat.id, "Выбор услуги отменен.", reply_markup=main_menu())
            return

    user_appointments[message.chat.id]['time'] = message.text
    user_id = message.chat.id
    service = user_appointments[message.chat.id]['service']
    master = user_appointments[message.chat.id]['master']
    date = user_appointments[message.chat.id]['date']
    time = message.text

    if add_appointment(user_id, service, master, date, time):
        bot.send_message(user_id, "Запись успешно создана!")
    else:
        bot.send_message(user_id, "Ошибка: не удалось создать запись. Попробуйте снова.")

    del user_appointments[message.chat.id]
    del user_steps[message.chat.id]
    bot.send_message(user_id, "Вы можете записаться снова или воспользоваться другими функциями.",
                     reply_markup=main_menu())


# Отмена записи
@bot.message_handler(func=lambda message: message.text == 'Отменить запись')
def cancel_appointment(message):
    user_id = message.chat.id
    appointments = get_user_appointments(user_id)

    if not appointments:
        bot.send_message(user_id, "У вас нет записей для отмены.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for appointment in appointments:
        appointment_text = f"{appointment[0]} | Мастер: {appointment[1]} | Дата: {appointment[2]} | Время: {appointment[3]}"
        markup.add(types.KeyboardButton(appointment_text))

    # Добавляем кнопку возврата
    markup.add(types.KeyboardButton('Назад'))

    bot.send_message(user_id, "Выберите запись для отмены:", reply_markup=markup)
    bot.register_next_step_handler(message, confirm_cancel_appointment)


# Подтверждение отмены записи
def confirm_cancel_appointment(message):
    if message.text == 'Назад':
        cancel_appointment(message)  # Возврат к отмене записи
        return

    user_id = message.chat.id
    appointment_details = message.text.split(' | ')

    if len(appointment_details) != 4:
        bot.send_message(user_id, "Ошибка: Неверный формат записи. Пожалуйста, попробуйте снова.")
        return

    service, master, date, time = appointment_details

    delete_appointment(user_id, date.split(': ')[1], time.split(': ')[1])
    bot.send_message(user_id, "Ваша запись успешно отменена.")
    bot.send_message(user_id, "Вы можете записаться снова или воспользоваться другими функциями.",
                     reply_markup=main_menu())


# Просмотр записей
@bot.message_handler(func=lambda message: message.text == 'Просмотреть записи')
def view_appointments(message):
    user_id = message.chat.id
    appointments = get_user_appointments(user_id)

    if not appointments:
        bot.send_message(user_id, "У вас нет записей.")
        return

    appointments_list = "\n".join(
        [f"{i + 1}. {app[0]} | Мастер: {app[1]} | Дата: {app[2]} | Время: {app[3]}" for i, app in
         enumerate(appointments)])
    bot.send_message(user_id, f"Ваши записи:\n{appointments_list}")


# Контакты
@bot.message_handler(func=lambda message: message.text == 'Контакты')
def show_contacts(message):
    bot.send_message(message.chat.id, "Контакты:\nТелефон: +123456789\nEmail: info@example.com")


# Помощь
@bot.message_handler(func=lambda message: message.text == 'Помощь')
def show_help(message):
    bot.send_message(message.chat.id, "Если у вас есть вопросы, пожалуйста, обращайтесь к нам!")


if __name__ == '__main__':
    init_db()
    bot.polling(none_stop=True)
