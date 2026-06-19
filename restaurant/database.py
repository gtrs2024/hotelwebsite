import sqlite3
import os
from werkzeug.security import generate_password_hash

DATABASE = os.path.join(os.path.dirname(__file__), 'restaurant.db')


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        password_hash TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
        customer_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT NOT NULL,
        preferred_date TEXT NOT NULL,
        preferred_time TEXT NOT NULL,
        guests INTEGER NOT NULL,
        special_requests TEXT,
        status TEXT DEFAULT 'New',
        counter_message TEXT,
        admin_note TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS gallery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_path TEXT NOT NULL,
        caption TEXT
    )''')

    # ── Migrations: safely add columns if they don't exist ──
    existing_cols = {row[1] for row in c.execute("PRAGMA table_info(reservations)")}
    for col, defn in [
        ('customer_id',     'INTEGER REFERENCES customers(id) ON DELETE SET NULL'),
        ('counter_message', 'TEXT'),
        ('admin_note',      'TEXT'),
    ]:
        if col not in existing_cols:
            c.execute(f'ALTER TABLE reservations ADD COLUMN {col} {defn}')

    # Seed admin
    c.execute('SELECT COUNT(*) FROM admins')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO admins (username, password_hash) VALUES (?, ?)',
                  ('admin', generate_password_hash('admin123')))

    # Seed menu items
    c.execute('SELECT COUNT(*) FROM menu_items')
    if c.fetchone()[0] == 0:
        items = [
            ('Starters', 'Lobster Bisque', 'Velvety bisque with Cognac cream and chive oil', 950),
            ('Starters', 'Seared Foie Gras', 'Pan-seared duck foie gras with fig compote and brioche', 1400),
            ('Starters', 'Burrata & Heirloom Tomato', 'Imported burrata with heirloom tomatoes and aged balsamic', 850),
            ('Starters', 'Truffle Arancini', 'Hand-rolled risotto bites with black truffle and parmesan', 750),
            ('Main Course', 'Wagyu Beef Tenderloin', 'A5 Wagyu with truffle jus, pomme purée and seasonal greens', 4800),
            ('Main Course', 'Pan-Roasted Chilean Sea Bass', 'Herb-crusted sea bass with saffron beurre blanc and asparagus', 2800),
            ('Main Course', 'Rack of Lamb', 'Frenched rack of lamb with rosemary jus and ratatouille', 3200),
            ('Main Course', 'Wild Mushroom Risotto', 'Carnaroli risotto with porcini, truffle oil and aged Parmigiano', 1600),
            ('Desserts', 'Dark Chocolate Soufflé', 'Warm Valrhona chocolate soufflé with vanilla crème anglaise', 850),
            ('Desserts', 'Mango Panna Cotta', 'Alphonso mango panna cotta with passion fruit coulis', 750),
            ('Desserts', 'Cheese Selection', 'Curated artisan cheese board with honeycomb and walnuts', 950),
            ('Desserts', 'Crêpes Suzette', 'Classic flambéed crêpes with Grand Marnier orange butter', 800),
            ('Beverages', 'Château Margaux 2018', 'Premier Grand Cru Classé, Bordeaux', 28000),
            ('Beverages', 'Dom Pérignon 2013', 'Prestige Cuvée Champagne, France', 32000),
            ('Beverages', 'House Cocktail – The Elara', 'Gin, elderflower, cucumber, sparkling water', 950),
            ('Beverages', 'Artisan Coffee Flight', 'Single-origin pour-overs: Ethiopia, Colombia, India', 650),
        ]
        c.executemany('INSERT INTO menu_items (category, name, description, price) VALUES (?,?,?,?)', items)

    # Seed gallery
    c.execute('SELECT COUNT(*) FROM gallery')
    if c.fetchone()[0] == 0:
        photos = [
            ('https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800&q=80', 'The Main Dining Room'),
            ('https://images.unsplash.com/photo-1559339352-11d035aa65de?w=800&q=80', 'Fine Dining Experience'),
            ('https://images.unsplash.com/photo-1600565193348-f74bd3c7ccdf?w=800&q=80', 'Our Executive Chef'),
            ('https://images.unsplash.com/photo-1551024601-bec78aea704b?w=800&q=80', 'Signature Desserts'),
            ('https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=800&q=80', 'Craft Cocktails'),
            ('https://images.unsplash.com/photo-1537047902294-62a40c20a6ae?w=800&q=80', 'Private Terrace'),
            ('https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&q=80', 'Ambient Lighting'),
            ('https://images.unsplash.com/photo-1550966871-3ed3cbe818b5?w=800&q=80', 'Wine Cellar'),
            ('https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=800&q=80', 'Seasonal Cuisine'),
        ]
        c.executemany('INSERT INTO gallery (image_path, caption) VALUES (?,?)', photos)

    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    print("Database initialised.")
