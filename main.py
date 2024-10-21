import telebot
import db
import user
import sqlite3

TOKEN = '8095038946:AAF-j8fR2g1f_zkVlshE4eYvqIkgOFQUN10'
bot = telebot.TeleBot(TOKEN)

db.init_db()

@bot.message_handler(commands=['start'])
def welcome(message):
    user_id = message.chat.id
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    cursor.execute('SELECT full_name FROM users WHERE user_id = ?', (user_id,))
    user_name = cursor.fetchone()

    if user_name is None:
        msg = bot.send_message(user_id, "Добро пожаловать! Как вас зовут?")
        bot.register_next_step_handler(msg, lambda msg: user.save_user_name(msg, bot))
    else:
        bot.send_message(user_id, f"Добро пожаловать, {user_name[0]}!", reply_markup=user.main_menu())
    conn.close()

@bot.message_handler(func=lambda message: message.text == 'Выбор услуги')
def handle_service(message):
    user.book_appointment(message, bot)

@bot.message_handler(func=lambda message: message.text == 'Просмотреть записи')
def handle_view_appointments(message):
    user.view_appointments(message, bot)

@bot.message_handler(func=lambda message: message.text == 'Отменить запись')
def handle_cancel_appointment(message):
    user.cancel_appointment(message, bot)

@bot.message_handler(func=lambda message: message.text == 'Контакты')
def handle_contacts(message):
    user.send_contacts(message, bot)

@bot.message_handler(func=lambda message: message.text == 'Помощь')
def handle_help(message):
    user.send_help(message, bot)

bot.polling(none_stop=True)
