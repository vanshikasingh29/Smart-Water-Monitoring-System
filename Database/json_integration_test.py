import sqlite3
import json

from databaseTables import insert_sensor_readings

# Connect to the database
conn = sqlite3.connect('water_quality.db')
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON")

with open ("test.json") as file:
    data = json.load(file)

    for item in data:
        insert_sensor_readings(1, ph_level= item["ph"],turbidity = item["turbidity"],temperature= item["temperature"])