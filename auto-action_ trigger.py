import sqlite3

# Connect to the database
conn = sqlite3.connect('water_quality.db')
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON")

cursor.execute('''
CREATE TRIGGER create_action_after_alert
AFTER INSERT ON alert
FOR EACH ROW
BEGIN
    INSERT INTO action (alert_id, action_type)
    SELECT 
        NEW.alert_id,
        aam.action_type
    FROM alert_action_map aam
    WHERE aam.alert_type = NEW.alert_type;
END;''')
