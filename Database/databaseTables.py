import sqlite3

# Connect to the database
conn = sqlite3.connect('water_quality.db')
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON")

# Tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS user (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    mac_address TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS sensor_readings (
    reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    ph_level REAL,
    turbidity REAL,
    temperature REAL,
    user_id INTEGER,
    
    FOREIGN KEY (user_id) REFERENCES user (user_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS alert (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    reading_id INTEGER NOT NULL,
    
    FOREIGN KEY (reading_id) REFERENCES sensor_readings (reading_id),
    FOREIGN KEY (alert_type) REFERENCES alert_definition(alert_type)
)
''')

cursor.execute(''' 
CREATE TABLE IF NOT EXISTS action (
    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    alert_id INTEGER NOT NULL,
    
    FOREIGN KEY (alert_id) REFERENCES alert (alert_id),
    FOREIGN KEY (action_type) REFERENCES action_definition(action_type)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS alert_definition (
    alert_type TEXT PRIMARY KEY,
    alert_description TEXT NOT NULL,
    max_value REAL,
    min_value REAL,
    severity TEXT,
    
    CHECK (max_value IS NULL OR min_value IS NULL OR max_value >= min_value)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS action_definition (
    action_type TEXT PRIMARY KEY,
    action_description TEXT NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS alert_action_map(
    alert_type TEXT NOT NULL,
    action_type TEXT NOT NULL,
    PRIMARY KEY (alert_type, action_type),

    FOREIGN KEY (alert_type) REFERENCES alert_definition(alert_type),
    FOREIGN KEY (action_type) REFERENCES action_definition(action_type)
);
''')

# insert functions
def insert_user(username, password):
    cursor.execute('''
    INSERT INTO user (username, password) VALUES (?, ?)''',
                   (username, password))


def insert_sensor_readings(user_id, sample, ph_level, turbidity, temperature):
    cursor.execute("""
                   INSERT INTO sensor_readings (sample, timestamp, ph_level, turbidity, temperature, user_id)
                   VALUES (?, datetime('now'), ?, ?, ?, ?)""",
                   (sample, ph_level, turbidity, temperature, user_id))

conn.commit()
conn.close()
