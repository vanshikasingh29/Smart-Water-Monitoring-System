import sqlite3

# Connect to the database
conn = sqlite3.connect('water_quality.db')
cursor = conn.cursor()

# insert alert_definition table
cursor.execute("""
insert into alert_definition (alert_type, alert_description, max_value, min_value) values 
('low_ph', 'pH level below safe range', 6.5, NULL),
('high_ph', 'pH level above safe range', NULL, 8.0),

-- turbidity alerts
('high_turbidity', 'Water turbidity exceeds safe level', NULL, 5.0),

-- temperature alerts
('high_temperature', 'Water temperature exceeds safe limit', NULL, 25.0),

-- critical contamination (no numeric threshold)
('contamination_detected', 'Potential contamination detected', NULL, NULL);
""")

# insert action definition
cursor.execute("""
insert into action_definition (action_type, action_description) values 
('add_acid', 'Reduce pH level of water'),
('add_base', 'Increase pH level of water'),

('activate_filter', 'Activate filtration system to clean water'),
('flush_system', 'Flush contaminated water out of the system'),

('cool_water', 'Activate cooling mechanism to reduce temperature'),

('shutdown_supply', 'Shut off water supply to prevent usage'),
('activate_uv', 'Activate UV sterilisation to disinfect water'),

('send_alert', 'Send notification to user via mobile app'),
('sound_alarm', 'Trigger audible alarm for immediate warning');
""")

cursor.execute("""
INSERT INTO alert_action_map (alert_type, action_type) VALUES
-- pH
('low_ph', 'add_base'),
('high_ph', 'add_acid'),

-- turbidity
('high_turbidity', 'activate_filter'),
('high_turbidity', 'flush_system'),

-- temperature
('high_temperature', 'cool_water'),

-- contamination (critical response)
('contamination_detected', 'shutdown_supply'),
('contamination_detected', 'activate_uv'),
('contamination_detected', 'send_alert'),
('contamination_detected', 'sound_alarm');
""")
conn.commit()
