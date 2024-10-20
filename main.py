import telebot
from user_mode import handle_user_commands
from admin_mode import handle_admin_commands
from db_utils import init_db

TOKEN = '8095038946:AAF-j8fR2g1f_zkVlshE4eYvqIkgOFQUN10'
bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных
init_db()

# Обработка пользовательских команд
handle_user_commands(bot)

# Обработка административных команд
handle_admin_commands(bot)

# Запуск бота
if __name__ == "__main__":
    bot.polling(none_stop=True)
