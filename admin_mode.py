from telebot import types
from db_utils import set_admin, remove_admin, is_admin, main_menu

ADMIN_LOGIN = 'admin'
ADMIN_PASSWORD = 'admin'

def handle_admin_commands(bot):
    @bot.message_handler(commands=['admin'])
    def admin_login(message):
        msg = bot.send_message(message.chat.id, "Введите логин:")
        bot.register_next_step_handler(msg, process_admin_login)

    def process_admin_login(message):
        if message.text == ADMIN_LOGIN:
            msg = bot.send_message(message.chat.id, "Введите пароль:")
            bot.register_next_step_handler(msg, process_admin_password)
        else:
            bot.send_message(message.chat.id, "Неверный логин.")

    def process_admin_password(message):
        if message.text == ADMIN_PASSWORD:
            set_admin(message.chat.id)
            bot.send_message(message.chat.id, "Вы вошли в админ-режим.", reply_markup=main_menu(True))
        else:
            bot.send_message(message.chat.id, "Неверный пароль.")

    @bot.message_handler(func=lambda message: message.text == 'Выйти из админ-режима')
    def exit_admin(message):
        remove_admin(message.chat.id)
        bot.send_message(message.chat.id, "Вы вышли из админ-режима.", reply_markup=main_menu(False))

