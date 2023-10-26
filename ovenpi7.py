# ovenpi7.py, increase resolution of PWM using time.sleep for off-time
import librtd
import RPi.GPIO as GPIO
import scurve
import time
import signal
import json
from datetime import datetime
from flask import Flask, Response, render_template, stream_with_context
from flask_socketio import SocketIO, emit
import threading
import random
import numpy as np
import sql

# globals to hold current readings and commands
top = 0.0
bottom = 0.0
front = 0.0
back = 0.0
probe1 = 0.0
probe2 = 0.0
pi = 0.0
ssr = 0.0
avg = 0
on_time = 0
timecount = 0
time0 = time.time()
timei = 0.0
setpoint = 25
command = 25
onoff = False
enableupper = False
enablelower = False
enablefan = False

database_file = './database/ovenpi7.db'
db = sql.open(database_file)
run_number = sql.read_last_run_number(db)

# PID gains
Kp = 0.05
Ki = 0.005   # integrator has 0.01 gain on top of this Ki

# PI controller
error = 0
integral = 0

# NaN sometimes appears in the temperture readings from librtd?
nan_count = 0

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
    sql.close(db)
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

def emit_data():
    while True:
        with lock:
            json_data = json.dumps(
            {'time':round(timei,0),'run_number':run_number,
            'top':top,'bottom':bottom,
            'front':front,'back':back,
            'probe1':probe1,'probe2':probe2,
            'pi':pi,'ssr':ssr,
            'setpoint':setpoint,'command':command,'avg':avg,
            'error':-error,'integral':integral,'on_time':on_time
            })
            
            # Send data to the 'update_chart' event
            socketio.emit('update_chart', json_data)
            #print("emit data {}",json_data)
        
        # Sleep long enough that browser client doesn't overload cpu
        time.sleep(5)

def record_data():
    db2 = sql.open(database_file)    
    while True:
        if onoff:
            with lock:
                # run time     top bottom front back    probe1 probe2 pi ssr     avg setpoint command on_time
                sql.insert_run_data(db2,(run_number,timei,top,bottom,front,back,probe1,probe2,pi,ssr,avg,setpoint,command,on_time))
        time.sleep(5)

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
    global ssr
    global upper
    global lower
    global fan
    global error
    global integral
    global avg
    global on_time
    global nan_count
    global command
    global sA
    global sStop
    global sError

    # local vars
    count = 0  
    time1 = 0.0
    time2 = 0.0
    temp = 0
    s = scurve.Scurve(target=0,x0=0,v0=0,vmax=0.1,amax=0.0002)

    while True:
        count = count + 1       # cycle counter for debug
        # fan control
        if enablefan == True:
            GPIO.output(16,1)   # fan on
            fan = 1
        else:
            GPIO.output(16,0)   # fan off
            fan = 0

        # read sensors and protect from NaN
        timei = time.time()-time0
        temp = librtd.get(0,1)
        if(np.isnan(temp)==False):
            top = temp
        else:
            nan_count = nan_count+1
        temp = librtd.get(0,7)
        if(np.isnan(temp)==False):
            bottom = temp
        else:
            nan_count = nan_count+1
        temp = librtd.get(0,8)
        if(np.isnan(temp)==False):
            front = temp
        else:
            nan_count = nan_count+1
        temp = librtd.get(0,4)
        if(np.isnan(temp)==False):
            back = temp
        else:
            nan_count = nan_count+1        
        temp = librtd.get(0,2)
        if(np.isnan(temp)==False):
            probe1 = temp
        else:
            nan_count = nan_count+1
        temp = librtd.get(0,3)
        if(np.isnan(temp)==False):
            probe2 = temp
        else:
            nan_count = nan_count+1
        temp = librtd.get(0,5)
        if(np.isnan(temp)==False):
            pi = temp
        else:
            nan_count = nan_count+1
        temp = librtd.get(0,6)
        if(np.isnan(temp)==False):
            ssr = temp
        else:
            nan_count = nan_count+1
        temp = 0.25*(top+bottom+front+back)
        if(np.isnan(temp)==False):
            avg = temp
        else:
            nan_count = nan_count+1

        if onoff == False:
            # oven is off
            on_time = 0
            error = 0
            integral = 0
            command = avg
            s.target = setpoint
            s.x = avg
            s.v = 0
            GPIO.output(21,0)   # upper off
            GPIO.output(12,0)   # lower off
            GPIO.output(16,0)   # fan off
        else:
            # oven is on
            with lock:
                # S-curve input shaping on the command
                s.target = setpoint
                s.step()
                command = s.x

                # compute error and integral
                error = command - avg
                integral = integral + 0.01*error
                if integral<0:
                    integral=0
                # limit authority of the integral term, 0.2 in open loop will reach max temp
                if integral>=0.2/Ki:
                    integral=0.2/Ki
                # compute on_time
                on_time = Kp*error + Ki*integral

                # limit max on_time so emit_data thread can get some time
                if on_time>0.9:
                    on_time=0.9

                # enforce a minimum on_time since SCRs only turn off at zero Vac
                if on_time<0.02:
                    on_time=0.0
 
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

        print("%5d: time=%5d   set=%7.3f  cmd=%7.3f   avg=%7.3f   e=%7.3f   int=%7.3f   on_time=%5.3f  nan_count=%3d" % 
              (count, timei,   setpoint,  command,    avg,        error,    integral,   on_time,       nan_count), flush=True)
        
        # delay 1 second minus the on_time
        time.sleep(1-on_time)
            
#start up threads
t1 = threading.Thread(target=controller,daemon=True)
t1.start()
t2 = threading.Thread(target=emit_data,daemon=True)
t2.start()
t3 = threading.Thread(target=record_data,daemon=True)
t3.start()

# flask webpage main
@app.route("/")
def index():
    initial_values = {
        'run_number':run_number,
        'setpoint':setpoint,
        'onoff':onoff,
        'enableupper':enableupper,
        'enablelower':enablelower,
        'enablefan':enablefan
    }

    return render_template('index7.html',initial_values=initial_values)

@socketio.on('update_setpoint')			
def update_setpoint(data):
    global setpoint
    print("Update setpoint to ",data)
    setpoint = data

@socketio.on('update_onoff')			
def update_onoff(data):
    global onoff
    global time0
    global run_number
    print("Update on/off to ",data)
    if data==True:
        time0=time.time()
        run_number+=1
        db3=sql.open(database_file)
        timestring=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print('starting test %2d at %s' % (run_number,timestring))
        sql.insert_run_summary(db3,(run_number,timestring,'default comment'))
    onoff = data

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
    socketio.run(app,host='0.0.0.0',debug=False)






