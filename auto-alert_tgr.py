import sqlite3

# Connect to the database
conn = sqlite3.connect('water_quality.db')
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON")

cursor.execute('''
CREATE TRIGGER IF NOT EXISTS auto_alert_trg
AFTER INSERT ON sensor_readings
FOR EACH ROW
BEGIN
    -- Low pH
    INSERT INTO alert (reading_id, alert_type)
    SELECT NEW.reading_id, 'low_ph'
    FROM alert_definition
    WHERE alert_type = 'low_ph'
      AND max_value IS NOT NULL
      AND NEW.ph_level IS NOT NULL
      AND NEW.ph_level < max_value;

    -- High pH
    INSERT INTO alert (reading_id, alert_type)
    SELECT NEW.reading_id, 'high_ph'
    FROM alert_definition
    WHERE alert_type = 'high_ph'
      AND min_value IS NOT NULL
      AND NEW.ph_level IS NOT NULL
      AND NEW.ph_level > min_value;

    -- High turbidity
    INSERT INTO alert (reading_id, alert_type)
    SELECT NEW.reading_id, 'high_turbidity'
    FROM alert_definition
    WHERE alert_type = 'high_turbidity'
      AND min_value IS NOT NULL
      AND NEW.turbidity IS NOT NULL
      AND NEW.turbidity > min_value;

    -- High temperature
    INSERT INTO alert (reading_id, alert_type)
    SELECT NEW.reading_id, 'high_temperature'
    FROM alert_definition
    WHERE alert_type = 'high_temperature'
      AND min_value IS NOT NULL
      AND NEW.temperature IS NOT NULL
      AND NEW.temperature > min_value;
END;
''')