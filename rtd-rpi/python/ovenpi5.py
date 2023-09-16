# ovenpi4.py, try to use web sockets
import librtd
import RPi.GPIO as GPIO
import time
import signal
import json
from datetime import datetime
from flask import Flask, Response, render_template, stream_with_context
from flask_socketio import SocketIO, emit
import threading
import random
import numpy as np

app = Flask(__name__)
#app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
#socketio = SocketIO(app, logger=True, engineio_logger=True)

# Make Control C exit properly after turning off the SSRs
def handler(signum,frame):
	print(" ")
	print("Control C detected, exiting ovenpi.py")
	print(" ")
	GPIO.output(21,0)
	GPIO.output(16,0)
	GPIO.output(12,0)
	GPIO.cleanup()
	exit(1)

signal.signal(signal.SIGINT, handler)
	
# Setup GPIOs that control the SSRs
GPIO.setwarnings(False)
# GPIO21 = Pin40 = Blue Wire = Upper Element
# GPIO16 = Pin36 = Yellow Wire = Fan
# GPIO12 = Pin32 = Green Wire = Lower Element
GPIO.setmode(GPIO.BCM)
GPIO.setup(21,GPIO.OUT)
GPIO.setup(16,GPIO.OUT)
GPIO.setup(12,GPIO.OUT)

# globals to hold current readings and commands
top = 0.0
bottom = 0.0
front = 0.0
back = 0.0
probe1 = 0.0
probe2 = 0.0
pi = 0.0
heatsink = 0.0
delta = 0.0
upper = 0.0
lower = 0.0
fan = 0.0
spare = 0.0
time0 = time.time()
timei = 0.0
setpoint = 23.5

# read 8 temps from rtd
def read_temps():
    # must declare these as globals otherwise they are redefined in local scope
    global timei
    global top
    global bottom
    global front
    global back
    global probe1
    global probe2
    global pi
    global heatsink
    global upper
    global lower
    global fan
    global delta
    global spare
    count = 0   # make this var a local

    while True:
        timei = datetime.now().strftime('%H:%M:%S')
        top = librtd.get(0,1)
        bottom = librtd.get(0,7)
        front = librtd.get(0,8)
        back = librtd.get(0,4)
        probe1 = librtd.get(0,2)
        probe2 = librtd.get(0,3)
        pi = librtd.get(0,5)
        heatsink = librtd.get(0,6)
        count = count + 1
        spare = count * 0.01
        delta = setpoint - top
        if count%10 == 0:
            upper = not upper
        if count%15 == 0:
            lower = not lower
        if count%20 == 0:
            fan = not fan
        #print("Count %6d: upper = %2d, lower = %2d, fan = %2d" % (count,upper,lower,fan), flush=True)
        time.sleep(1)

#start up threads
t1 = threading.Thread(target=read_temps,daemon=True)
t1.start()

def emit_data():
    while True:
        json_data = json.dumps(
        {'time':timei,\
        'top':top,'probe1':probe1,\
        'probe2':probe2,'back':back,\
        'pi':pi,'heatsink':heatsink,\
        'bottom':bottom,'front':front,\
        'delta':delta,'spare':spare,\
        'upper':upper+2.2,'lower':lower+1.1,'fan':fan\
        })
        
        # Send data to the 'update_chart' event
        socketio.emit('update_chart', json_data)
        #print("emit data {}",json_data)
        
        # Sleep for a while (adjust this based on your desired update rate)
        time.sleep(5)

# flask webpage main
@app.route("/")
def index():
	return render_template('index5.html')

@socketio.on('update_setpoint')			
def update_setpoint(data):
    print("Update setpoint to ",data)

if __name__=="__main__":
#	app.run(host='0.0.0.0',debug=False)
    socketio.start_background_task(target=emit_data)
    socketio.run(app,host='0.0.0.0',debug=False)






