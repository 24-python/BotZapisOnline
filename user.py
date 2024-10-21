import db
from telebot import types
from datetime import datetime, timedelta

services = {
    'Мужская стрижка': ['Мастер 1', 'Мастер 2'],
    'Женская стрижка': ['Мастер 3', 'Мастер 4'],
    'Окрашивание': ['Мастер 5', 'Мастер 6']
}

user_appointments = {}
user_steps = {}

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

    db_conn = db.init_db()
    db_conn.cursor.execute('''INSERT OR REPLACE INTO users (user_id, username, full_name) 
                              VALUES (?, ?, ?)''', (user_id, message.from_user.username, full_name))
    db_conn.conn.commit()
    db_conn.close()

    bot.send_message(user_id, f"Приятно познакомиться, {full_name}! Выбирайте услугу", reply_markup=main_menu())

def book_appointment(message, bot):
    user_appointments[message.chat.id] = {}
    user_steps[message.chat.id] = 'service'

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for service in services.keys():
        markup.add(types.KeyboardButton(service))

    markup.add(types.KeyboardButton('Назад'))
    bot.send_message(message.chat.id, "Выберите услугу:", reply_markup=markup)
    bot.register_next_step_handler(message, select_master)

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
    bot.register_next_step_handler(message, select_date)

def select_date(message, bot):
    if message.text == 'Назад':
        if user_steps.get(message.chat.id) == 'master':
            return book_appointment(message, bot)

    user_appointments[message.chat.id]['master'] = message.text
    user_steps[message.chat.id] = 'date'

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    today = datetime.now().date()
    dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]

    for date in dates:
        markup.add(types.KeyboardButton(date))

    markup.add(types.KeyboardButton('Назад'))
    bot.send_message(message.chat.id, "Выберите дату:", reply_markup=markup)
    bot.register_next_step_handler(message, select_time)

def select_time(message, bot):
    user_appointments[message.chat.id]['date'] = message.text
    user_steps[message.chat.id] = 'time'

    now = datetime.now()
    available_times = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00']

    if user_appointments[message.chat.id]['date'] == now.strftime('%Y-%m-%d'):
        available_times = [time for time in available_times if time > now.strftime('%H:%M')]

    booked_times = db.get_booked_times(user_appointments[message.chat.id]['date'],
                                       user_appointments[message.chat.id]['master'])
    free_times = [time for time in available_times if time not in booked_times]

    if free_times:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for time in free_times:
            markup.add(types.KeyboardButton(time))
        markup.add(types.KeyboardButton('Назад'))

        bot.send_message(message.chat.id, "Выберите время:", reply_markup=markup)
        bot.register_next_step_handler(message, confirm_appointment)
    else:
        bot.send_message(message.chat.id, "Нет свободных слотов.", reply_markup=main_menu())

def confirm_appointment(message, bot):
    if message.text == 'Назад':
        return select_time(message, bot)

    user_id = message.chat.id
    selected_time = message.text

    success = db.add_appointment(user_id,
                                 user_appointments[user_id]['service'],
                                 user_appointments[user_id]['master'],
                                 user_appointments[user_id]['date'],
                                 selected_time)

    if success:
        bot.send_message(user_id, "Запись успешно добавлена!", reply_markup=main_menu())
    else:
        bot.send_message(user_id, "Ошибка! Запись уже существует.", reply_markup=main_menu())

def cancel_appointment(message, bot):
    user_id = message.chat.id
    appointments = db.get_user_appointments(user_id)

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

def process_cancellation(message, bot):
    if message.text == 'Назад':
        bot.send_message(message.chat.id, "Отмена отмены.", reply_markup=main_menu())
        return

    user_id = message.chat.id
    try:
        service_master, date_time = message.text.split(" на ")
        service, master = service_master.split(" - ")
        date, time = date_time.split(" в ")

        db.delete_appointment(user_id, date, time)
        bot.send_message(user_id, "Запись отменена.", reply_markup=main_menu())
    except ValueError:
        bot.send_message(user_id, "Ошибка формата записи.", reply_markup=main_menu())

def view_appointments(message, bot):
    user_id = message.chat.id
    appointments = db.get_user_appointments(user_id)

    if not appointments:
        bot.send_message(user_id, "У вас нет записей.", reply_markup=main_menu())
        return

    response = "Ваши записи:\n"
    for appointment in appointments:
        service, master, date, time = appointment
        response += f"{service} - {master} на {date} в {time}\n"

    bot.send_message(user_id, response, reply_markup=main_menu())

def contacts(message, bot):
    bot.send_message(message.chat.id, "Контакты:\nТелефон: +7 (123) 456-78-90\nEmail: example@example.com",
                     reply_markup=main_menu())

def help_message(message, bot):
    bot.send_message(message.chat.id, "Помощь:\n1. Чтобы записаться, выберите 'Выбор услуги'.\n"
                                      "2. Для отмены записи выберите 'Отменить запись'.\n"
                                      "3. Чтобы просмотреть записи, выберите 'Просмотреть записи'.",
                     reply_markup=main_menu())
