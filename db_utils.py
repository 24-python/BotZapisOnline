import sqlite3
from telebot import types
def init_db():
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, is_admin INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS appointments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, service TEXT, master TEXT, date TEXT, time TEXT, UNIQUE(user_id, date, time))''')
    conn.commit()
    conn.close()

def get_user_appointments(user_id):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT service, master, date, time FROM appointments WHERE user_id = ?''', (user_id,))
    appointments = cursor.fetchall()
    conn.close()
    return appointments

def add_appointment(user_id, service, master, date, time):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''INSERT INTO appointments (user_id, service, master, date, time) VALUES (?, ?, ?, ?, ?)''', (user_id, service, master, date, time))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_appointment(user_id, date, time):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    cursor.execute('''DELETE FROM appointments WHERE user_id = ? AND date = ? AND time = ?''', (user_id, date, time))
    conn.commit()
    conn.close()

def is_admin(user_id):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT is_admin FROM users WHERE user_id = ?''', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

def set_admin(user_id):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    cursor.execute('''UPDATE users SET is_admin = 1 WHERE user_id = ?''', (user_id,))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    cursor.execute('''UPDATE users SET is_admin = 0 WHERE user_id = ?''', (user_id,))
    conn.commit()
    conn.close()

def main_menu(is_admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Записаться на стрижку')
    btn2 = types.KeyboardButton('Отменить запись')
    btn3 = types.KeyboardButton('Просмотреть записи')
    btn4 = types.KeyboardButton('Контакты')
    btn5 = types.KeyboardButton('Помощь')
    markup.add(btn1, btn2, btn3, btn4, btn5)

    if is_admin:
        btn_admin = types.KeyboardButton('Админ-панель')
        btn_exit_admin = types.KeyboardButton('Выйти из админ-режима')
        markup.add(btn_admin, btn_exit_admin)

    return markup
def notify_admins(bot, message):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE is_admin = 1')
    admins = cursor.fetchall()
    conn.close()

    for admin in admins:
        bot.send_message(admin[0], message)
