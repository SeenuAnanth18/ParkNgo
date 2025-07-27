import sqlite3

def init_db():
    with sqlite3.connect('parking.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            contact TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS parking_spaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            area TEXT NOT NULL,
            price_per_hour REAL NOT NULL,
            total_slots INTEGER NOT NULL,
            available_slots INTEGER NOT NULL,
            description TEXT,
            image TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    space_id INTEGER,
    hours INTEGER NOT NULL,
    booking_date TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (space_id) REFERENCES parking_spaces (id)
)''')
        conn.commit()

def get_db():
    conn = sqlite3.connect('parking.db')
    conn.row_factory = sqlite3.Row
    return conn