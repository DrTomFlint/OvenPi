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
	GPIO.output(12,0)
	GPIO.output(16,0)
	GPIO.cleanup()
	exit(1)

signal.signal(signal.SIGINT, handler)
	
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
timeon = 0
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
    global deltalim
    global integral
    global avg
    global timeon
    global timecount
    count = 0   # make this var a local

    while True:
#        timei = datetime.now().strftime('%H:%M:%S')
        timei = time.time()-time0
        top = librtd.get(0,1)
        bottom = librtd.get(0,7)
        front = librtd.get(0,8)
        back = librtd.get(0,4)
        probe1 = librtd.get(0,2)
        probe2 = librtd.get(0,3)
        pi = librtd.get(0,5)
        heatsink = librtd.get(0,6)
        count = count + 1
        spare = count
        avg = 0.25*(top+bottom+front+back)
        delta = setpoint - avg
        # once every N seconds update the time on
        if count==N:
            count=0
        #     deltalim=delta
        #     if delta>10:
        #         deltalim=10
        #     if delta>20:
        #         deltalim=0

        #     if onoff==True:
        #         integral=integral+deltalim
        #     else:
        #         integral=0

        #     if delta>0:
        #         timeon = np.ceil(0.1*delta+0.01*integral)
        #         if timeon>N:
        #             timeon=N
        #     else:
        #         timeon=0

        # TEST do an open loop step response
            timeon = 1
            timecount = timeon

        
        if onoff == False:
            # oven is off
            timeon = 0
            timecount = 0
            upper = 0
            lower = 0
            fan = 0
            GPIO.output(21,0)   # upper off
            GPIO.output(12,0)   # lower off
            GPIO.output(16,0)   # fan off
        else:
            # oven is on
            if enablefan == True:
                GPIO.output(16,1)   # fan on
                fan = 1
            else:
                GPIO.output(16,0)   # fan off
                fan = 0
            if timecount > 0:
                # on time has not expired
                if enableupper == True:
                    GPIO.output(21,1)   # upper on
                    upper = timeon
                if enablelower == True:
                    GPIO.output(12,1)   # lower on
                    lower = timeon
                timecount = timecount-1
            else:
                # on time has expired
                GPIO.output(21,0)   # upper off
                GPIO.output(12,0)   # lower off
                upper = timeon
                lower = timeon

        print("Count %4d: set=%5.1f avg=%5.1f delta=%5.1f integral=%5.1f timeon=%2d timecount=%2d" % 
              (count,  setpoint,    avg,      delta,     integral,      timeon,     timecount), flush=True)
        time.sleep(1)

#start up threads
t1 = threading.Thread(target=read_temps,daemon=True)
t1.start()

def emit_data():
    while True:
        json_data = json.dumps(
        {'time':round(timei,0),'avg':round(avg,1),'timeon':timeon,\
        'top':round(top,1),'probe1':round(probe1,1),\
        'probe2':round(probe2,1),'back':round(back,1),\
        'pi':round(pi,1),'heatsink':round(heatsink,1),\
        'bottom':round(bottom,1),'front':round(front,1),\
        'setpoint':round(setpoint,1),'delta':round(-delta,1),\
        'upper':upper,'lower':lower,'fan':fan,\
        'integral':round(integral,1)\
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






