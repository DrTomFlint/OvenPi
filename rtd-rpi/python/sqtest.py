#!/usr/bin/env python3
import sqlite3

# create tables
db = sqlite3.connect('./database/ovenpi1.db')
cursor = db.cursor()
q_create_run_data ='''
    CREATE TABLE IF NOT EXISTS run_data(
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        run_number INTEGER,
        time INTEGER,
        top REAL,
        bottom REAL,
        avg REAL,
        setpoint REAL,
        command REAL,
        on_time REAL,
        FOREIGN KEY (run_number) REFERENCES run_summary(run_number)
    )'''

cursor.execute(q_create_run_data)

q_create_run_summary ='''
    CREATE TABLE IF NOT EXISTS run_summary(
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        run_number INTEGER,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        comment TEXT
    )'''

cursor.execute(q_create_run_summary)

db.commit()
db.close()

# create 2 runs with run_data and run_summary
run_number = 1
data1 = [
    (run_number, 1, 50.0, 40.0, 40.0, 47.0, 46.8, 0.123),
    (run_number, 2, 51.0, 40.1, 41.1, 47.0, 46.9, 0.124),
    (run_number, 3, 52.0, 40.2, 42.2, 47.0, 47.0, 0.125),
    (run_number, 4, 53.0, 40.3, 43.3, 47.0, 47.1, 0.126),
]
summary1 = (1, '2023-09-12 10:00:00', 'bake a stealie')

run_number = 2
data2 = [
    (run_number, 1, 80.0, 60.0, 70.0, 74.0, 76.8, 0.223),
    (run_number, 2, 81.0, 60.1, 71.1, 74.0, 76.9, 0.224),
    (run_number, 3, 82.0, 60.2, 72.2, 74.0, 77.0, 0.225),
    (run_number, 4, 83.0, 60.3, 73.3, 74.0, 77.1, 0.226),
    (run_number, 5, 84.0, 60.4, 73.4, 74.0, 77.2, 0.227),
    (run_number, 6, 85.0, 60.5, 73.5, 74.0, 77.3, 0.228),
]
summary2 = (run_number, '2023-09-12 11:45:05', 'bake some lovecoins')

# insert data into tables
db = sqlite3.connect('./database/ovenpi1.db')
cursor = db.cursor()

q_insert_run_data='''
    INSERT INTO run_data (run_number, time, top, bottom, avg, setpoint, command, on_time)
    VALUES (?,?,?,?,?,?,?,?)
'''
q_insert_run_summary='''
    INSERT INTO run_summary (run_number, start_time, comment)
    VALUES (?,?,?)
'''

cursor.executemany(q_insert_run_data,data1)
cursor.execute(q_insert_run_summary,summary1)
cursor.executemany(q_insert_run_data,data2)
cursor.execute(q_insert_run_summary,summary2)

db.commit()
db.close()

