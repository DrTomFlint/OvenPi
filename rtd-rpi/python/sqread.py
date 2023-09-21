#!/usr/bin/env python3
import sqlite3

# create tables
db = sqlite3.connect('./database/ovenpi1.db')
cursor = db.cursor()

run_number = 2

q_read_data = '''
    SELECT *
    FROM run_data
    WHERE run_number = ?
'''

q_read_summary = '''
    SELECT *
    FROM run_summary
    WHERE run_number = ?
'''

cursor.execute(q_read_summary,str(run_number))
row = cursor.fetchone()
while row:
    print('id:        ',row[0])
    print('run number:',row[1])
    print('start time:',row[2])
    print('comment:   ',row[3])
    row = cursor.fetchone()


cursor.execute(q_read_data,str(run_number))

row = cursor.fetchone()
while row:
    print('id:        ',row[0])
    print('run number:',row[1])
    print('top:       ',row[2])
    print('bottom:    ',row[3])
    print('avg:       ',row[4])
    print('setpoint:  ',row[5])
    print('command:   ',row[6])
    print('on_time:   ',row[7])
    row = cursor.fetchone()

db.close()

