# Выбор мастера
def select_master(message):
    user_id = message.chat.id
    user_appointments[user_id]['service'] = message.text  # Сохраняем выбранную услугу

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for master in masters:
        markup.add(types.KeyboardButton(master))

    bot.send_message(user_id, "Выберите мастера:", reply_markup=markup)
    bot.register_next_step_handler(message, select_date)


# Выбор даты
def select_date(message):
    user_id = message.chat.id
    user_appointments[user_id]['master'] = message.text  # Сохраняем выбранного мастера

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    today = datetime.now().date()
    dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    for date in dates:
        markup.add(types.KeyboardButton(date))

    bot.send_message(user_id, "Выберите дату:", reply_markup=markup)
    bot.register_next_step_handler(message, select_time)


# Выбор времени
def select_time(message):
    user_id = message.chat.id
    selected_date = message.text  # Сохраняем выбранную дату
    user_appointments[user_id]['date'] = selected_date

    selected_master = user_appointments[user_id]['master']
    now = datetime.now()

    available_times = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00']

    # Если выбрана сегодняшняя дата, исключаем прошедшие временные слоты
    if selected_date == now.strftime('%Y-%m-%d'):
        available_times = [time for time in available_times if time > now.strftime('%H:%M')]

    # Проверяем занятые слоты для выбранного мастера и даты
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    cursor.execute('SELECT time FROM appointments WHERE date = ? AND master = ?', (selected_date, selected_master))
    booked_times = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Исключаем занятые слоты
    free_times = [time for time in available_times if time not in booked_times]

    if free_times:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for time in free_times:
            markup.add(types.KeyboardButton(time))

        bot.send_message(user_id, "Выберите время:", reply_markup=markup)
        bot.register_next_step_handler(message, confirm_appointment)
    else:
        bot.send_message(user_id,
                         "Нет доступных временных слотов для выбранной даты. Пожалуйста, выберите другую дату.")
        bot.register_next_step_handler(message, select_date)  # Возвращаем пользователя к выбору даты


# Подтверждение записи
def confirm_appointment(message):
    user_id = message.chat.id
    selected_time = message.text  # Сохраняем выбранное время
    user_appointments[user_id]['time'] = selected_time

    user_data = user_appointments[user_id]

    # Добавляем запись в базу данных
    success = add_appointment(
        user_id,
        user_data['service'],
        user_data['master'],
        user_data['date'],
        user_data['time']
    )

    if success:
        bot.send_message(user_id, "Ваша запись успешно создана!")
        notify_admins(
            f"Новая запись: {user_data['service']} к {user_data['master']} на {user_data['date']} {user_data['time']}.")
    else:
        bot.send_message(user_id, "Произошла ошибка при создании записи. Попробуйте снова.")

    # Удаляем временные данные
    user_appointments.pop(user_id, None)

    bot.send_message(user_id, "Возвращаю вас в главное меню.", reply_markup=main_menu(is_admin(user_id)))
