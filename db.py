import sqlite3

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

def save_user_name(user_id, full_name):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    cursor.execute('''INSERT OR REPLACE INTO users (user_id, full_name) 
                      VALUES (?, ?)''', (user_id, full_name))
    conn.commit()
    conn.close()

def add_appointment(user_id, service, master, date, time):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''INSERT INTO appointments (user_id, service, master, date, time) 
                          VALUES (?, ?, ?, ?, ?)''', (user_id, service, master, date, time))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False

    conn.close()
    return success

def get_user_appointments(user_id):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    cursor.execute('''SELECT service, master, date, time FROM appointments WHERE user_id = ?''', (user_id,))
    appointments = cursor.fetchall()

    conn.close()
    return appointments

def delete_appointment(user_id, date, time):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()

    cursor.execute('''DELETE FROM appointments WHERE user_id = ? AND date = ? AND time = ?''', (user_id, date, time))
    conn.commit()
    conn.close()
