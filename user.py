import db
from telebot import types
from datetime import datetime, timedelta
import schedule
import time
import threading
import sqlite3
import pytz  # Для работы с часовыми поясами

services = {
    'Мужская стрижка': ['Мастер 1', 'Мастер 2'],
    'Женская стрижка': ['Мастер 3', 'Мастер 4'],
    'Окрашивание': ['Мастер 5', 'Мастер 6']
}

user_appointments = {}
user_steps = {}
user_timezones = {}  # Хранение часовых поясов пользователей

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Выбор услуги')
    btn2 = types.KeyboardButton('Отменить запись')
    btn3 = types.KeyboardButton('Просмотреть записи')
    btn4 = types.KeyboardButton('Контакты')
    btn5 = types.KeyboardButton('Помощь')
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup

def save_user_name(message, bot):
    full_name = message.text
    user_id = message.chat.id

    db.save_user_name(user_id, full_name)

    bot.send_message(user_id, f"Приятно познакомиться, {full_name}! Выбирайте услугу", reply_markup=main_menu())

def book_appointment(message, bot):
    user_appointments[message.chat.id] = {}
    user_steps[message.chat.id] = 'service'

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for service in services.keys():
        markup.add(types.KeyboardButton(service))

    markup.add(types.KeyboardButton('Назад'))

    bot.send_message(message.chat.id, "Выберите услугу:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda msg: select_master(msg, bot))

def select_master(message, bot):
    if message.text == 'Назад':
        bot.send_message(message.chat.id, "Выберите услугу:", reply_markup=main_menu())
        return

    user_appointments[message.chat.id]['service'] = message.text
    user_steps[message.chat.id] = 'master'

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    selected_service = message.text
    for master in services[selected_service]:
        markup.add(types.KeyboardButton(master))

    markup.add(types.KeyboardButton('Назад'))

    bot.send_message(message.chat.id, "Выберите мастера:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda msg: select_date(msg, bot))

def select_date(message, bot):
    if message.text == 'Назад':
        return book_appointment(message, bot)

    user_appointments[message.chat.id]['master'] = message.text
    user_steps[message.chat.id] = 'date'

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    today = datetime.now().date()

    dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
    for date in dates:
        markup.add(types.KeyboardButton(date))

    markup.add(types.KeyboardButton('Назад'))

    bot.send_message(message.chat.id, f"Выберите дату для мастера {message.text}:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda msg: select_time(msg, bot))

def select_time(message, bot):
    if message.text == 'Назад':
        return select_date(message, bot)

    user_appointments[message.chat.id]['date'] = message.text
    selected_master = user_appointments[message.chat.id]['master']
    user_steps[message.chat.id] = 'time'

    now = datetime.now()

    available_times = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00']

    if message.text == now.strftime('%Y-%m-%d'):
        available_times = [time for time in available_times if time > now.strftime('%H:%M')]

    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    cursor.execute('SELECT time FROM appointments WHERE date = ? AND master = ?', (message.text, selected_master))
    booked_times = [row[0] for row in cursor.fetchall()]
    conn.close()

    free_times = [time for time in available_times if time not in booked_times]

    if free_times:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for time in free_times:
            markup.add(types.KeyboardButton(time))

        markup.add(types.KeyboardButton('Назад'))

        bot.send_message(message.chat.id, f"Выберите время для {selected_master} на {message.text}:",
                         reply_markup=markup)
        bot.register_next_step_handler(message, lambda msg: confirm_appointment(msg, bot))
    else:
        bot.send_message(message.chat.id, "К сожалению, нет доступного времени на выбранную дату.",
                         reply_markup=main_menu())

def confirm_appointment(message, bot):
    if message.text == 'Назад':
        return select_time(message, bot)

    selected_time = message.text
    user_id = message.chat.id

    success = db.add_appointment(user_id, user_appointments[user_id]['service'],
                                 user_appointments[user_id]['master'],
                                 user_appointments[user_id]['date'], selected_time)

    if success:
        bot.send_message(user_id, "Запись успешно добавлена!", reply_markup=main_menu())
        schedule_reminder(bot, user_id, user_appointments[user_id]['service'],
                          user_appointments[user_id]['master'],
                          user_appointments[user_id]['date'], selected_time)
    else:
        bot.send_message(user_id, "Ошибка: Запись на это время уже существует.", reply_markup=main_menu())

def schedule_reminder(bot, user_id, service, master, date, time):
    # Определяем часовой пояс пользователя
    user_timezone = user_timezones.get(user_id, 'Europe/Moscow')  # По умолчанию 'Europe/Moscow'
    tz = pytz.timezone(user_timezone)

    # Определяем время напоминания (за 24 часа до записи)
    appointment_time = tz.localize(datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M"))
    reminder_time = appointment_time - timedelta(days=1)

    schedule.every().day.at(reminder_time.strftime("%H:%M")).do(send_reminder, bot, user_id, service, master, date, time)

    # Запускаем планировщик в отдельном потоке
    threading.Thread(target=run_schedule).start()

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)

def send_reminder(bot, user_id, service, master, date, time):
    bot.send_message(user_id, f"НАПОМИНАНИЕ! у вас запись: {service} у {master} на {date} в {time}.")

def view_appointments(message, bot):
    user_id = message.chat.id
    appointments = db.get_user_appointments(user_id)

    if appointments:
        appointment_list = "\n".join([f"{service}, {master}, {date}, {time}" for service, master, date, time in appointments])
        bot.send_message(user_id, f"Ваши записи:\n{appointment_list}")
    else:
        bot.send_message(user_id, "У вас нет записей.", reply_markup=main_menu())

def cancel_appointment(message, bot):
    user_id = message.chat.id
    appointments = db.get_user_appointments(user_id)

    if appointments:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for service, master, date, time in appointments:
            markup.add(types.KeyboardButton(f"{service}, {master}, {date} {time}"))

        markup.add(types.KeyboardButton('Назад'))
        bot.send_message(user_id, "Выберите запись для отмены (вид услуги, мастер, дата, время):", reply_markup=markup)
        bot.register_next_step_handler(message, lambda msg: confirm_cancel(msg, bot))
    else:
        bot.send_message(user_id, "У вас нет записей.", reply_markup=main_menu())

def confirm_cancel(message, bot):
    if message.text == 'Назад':
        bot.send_message(message.chat.id, "Отмена записи отменена.", reply_markup=main_menu())
        return

    full_info = message.text
    try:
        service, master, datetime_info = full_info.split(', ', 2)
        date, time = datetime_info.split()
        user_id = message.chat.id
        db.delete_appointment(user_id, date, time)

        bot.send_message(user_id, f"Запись на {service}, мастер {master}, {date} {time} отменена.", reply_markup=main_menu())
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат записи. Попробуйте снова.", reply_markup=main_menu())

def send_contacts(message, bot):
    bot.send_message(message.chat.id, "Наши контакты: +7 (123) 456-78-90, ул. Примерная, д. 1", reply_markup=main_menu())

def send_help(message, bot):
    bot.send_message(message.chat.id, "Для записи выберите услугу. Если нужна помощь, свяжитесь с нами по телефону.", reply_markup=main_menu())
