# ovenpi6.py, increase resolution of PWM using time.sleep for off-time
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
	GPIO.output(12,0)
	GPIO.output(16,0)
	GPIO.cleanup()
	exit(1)

signal.signal(signal.SIGINT, handler)

# Create a mutex to prevent interruption of the controller thread
lock = threading.Lock()
	
# Setup GPIOs that control the SSRs
GPIO.setwarnings(False)
# GPIO21 = Pin40 = Blue Wire = Upper Element
# GPIO12 = Pin32 = Green Wire = Lower Element
# GPIO16 = Pin36 = Yellow Wire = Fan
GPIO.setmode(GPIO.BCM)
GPIO.setup(21,GPIO.OUT)
GPIO.setup(12,GPIO.OUT)
GPIO.setup(16,GPIO.OUT)

# globals to hold current readings and commands
top = 0.0
bottom = 0.0
front = 0.0
back = 0.0
probe1 = 0.0
probe2 = 0.0
pi = 0.0
heatsink = 0.0
avg = 0
on_time = 0
timecount = 0
delta = 0.0
deltalim = 0.0
integral = 0.0
upper = 0.0
lower = 0.0
fan = 0.0
time0 = time.time()
timei = 0.0
setpoint = 25
onoff = False
enableupper = False
enablelower = False
enablefan = False
N = 10
# PID gains
Kp = 0.075
Ki = 0.0
Kd = 0.0
# PID controller implementation
K1 = Kp+Ki+Kd
K2 = -Kp-2*Kd
K3 = Kd
e = 0
e1 = 0
e2 = 0
d = 0

# read 8 temps from rtd
def controller():
    # call out globals that are modified within this function
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
    global e
    global e1
    global e2
    global d
    global avg
    global on_time
    # local vars
    count = 0  
    time1 = 0.0
    time2 = 0.0

    while True:
        count = count + 1       # cycle counter for debug
        # fan control
        if enablefan == True:
            GPIO.output(16,1)   # fan on
            fan = 1
        else:
            GPIO.output(16,0)   # fan off
            fan = 0

        # read sensors
        timei = time.time()-time0
        top = librtd.get(0,1)
        bottom = librtd.get(0,7)
        front = librtd.get(0,8)
        back = librtd.get(0,4)
        probe1 = librtd.get(0,2)
        probe2 = librtd.get(0,3)
        pi = librtd.get(0,5)
        heatsink = librtd.get(0,6)
        avg = 0.25*(top+bottom+front+back)

        # PID controller, always compute errors
        e2 = e1
        e1 = e
        e = setpoint - avg

        if onoff == False:
            # oven is off
            on_time = 0
            GPIO.output(21,0)   # upper off
            GPIO.output(12,0)   # lower off
            GPIO.output(16,0)   # fan off
        else:
            # PID controller, compute on_time
            with lock:
                if e>0:
                    d = K1*e + K2*e1 + K3*e2
                    # limit max on_time so emit_data thread can get some time
                    on_time = on_time + d
                    if on_time>0.9:
                        on_time=0.9
                else:
                    on_time=0

                if on_time > 0:
                    # turn on output
                    time1=time.time()
                    if enableupper == True:
                        GPIO.output(21,1)   # upper on
                    if enablelower == True:
                        GPIO.output(12,1)   # lower on
                    # delay for timeon
                    time.sleep(on_time)
                    # turn off output
                    time2=time.time()
                    GPIO.output(21,0)   # upper off
                    GPIO.output(12,0)   # lower off
                else:
                    # output should be entirely off
                    time1=time2=0
                    GPIO.output(21,0)   # upper off
                    GPIO.output(12,0)   # lower off

        print("%5d: time=%5d    set=%5.1f    avg=%5.1f    e=%5.1f    on_time=%5.3f    actual=%5.3f" % 
              (count, timei,    setpoint,    avg,         e,         on_time,         time2-time1), flush=True)
        
        # delay 1 second minus the on_time
        time.sleep(1-on_time)

#start up threads
t1 = threading.Thread(target=controller,daemon=True)
t1.start()

def emit_data():
    while True:
        with lock:
            json_data = json.dumps(
            {'time':round(timei,0),
            'top':round(top,1),'bottom':round(bottom,1),
            'front':round(front,1),'back':round(back,1),
            'probe1':round(probe1,1),'probe2':round(probe2,1),
            'pi':round(pi,1),'heatsink':round(heatsink,1),
            'setpoint':round(setpoint,1),'avg':round(avg,1),
            'e':round(-e,1),'on_time':round(on_time,3)
            })
            
            # Send data to the 'update_chart' event
            socketio.emit('update_chart', json_data)
            #print("emit data {}",json_data)
        
        # Sleep for a while (adjust this based on your desired update rate)
        time.sleep(5)

# flask webpage main
@app.route("/")
def index():
	return render_template('index6.html')

@socketio.on('update_setpoint')			
def update_setpoint(data):
    global setpoint
    print("Update setpoint to ",data)
    setpoint = data

@socketio.on('update_onoff')			
def update_onoff(data):
    global onoff
    global time0
    print("Update on/off to ",data)
    onoff = data
    if data==True:
        time0=time.time()
        print(round(time0,0))

@socketio.on('update_upper')			
def update_upper(data):
    global enableupper
    print("Update upper enable to ",data)
    enableupper = data

@socketio.on('update_lower')			
def update_lower(data):
    global enablelower
    print("Update lower enable to ",data)
    enablelower = data

@socketio.on('update_fan')			
def update_fan(data):
    global enablefan
    print("Update fan enable to ",data)
    enablefan = data

if __name__=="__main__":
#	app.run(host='0.0.0.0',debug=False)
    socketio.start_background_task(target=emit_data)
    socketio.run(app,host='0.0.0.0',debug=False)






