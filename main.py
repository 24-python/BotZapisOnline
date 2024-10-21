import telebot
import user
import db

TOKEN = 'your_bot_token_here'
bot = telebot.TeleBot(TOKEN)

db.init_db()

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Добро пожаловать! Как вас зовут?")
    bot.register_next_step_handler(message, lambda msg: user.save_user_name(msg, bot))

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text == 'Выбор услуги':
        user.book_appointment(message, bot)
    elif message.text == 'Отменить запись':
        user.cancel_appointment(message, bot)
    elif message.text == 'Просмотреть записи':
        user.view_appointments(message, bot)
    elif message.text == 'Контакты':
        user.contacts(message, bot)
    elif message.text == 'Помощь':
        user.help_message(message, bot)
    else:
        bot.send_message(message.chat.id, "Выберите команду из меню.", reply_markup=user.main_menu())

bot.polling()
