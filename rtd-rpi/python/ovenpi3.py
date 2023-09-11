# ovenpi3.py, try to read the rtds and show results on a formatted webpage
import librtd
import RPi.GPIO as GPIO
import time
import signal
import json
from datetime import datetime
from flask import Flask, Response, render_template, stream_with_context
import threading
import random
import numpy as np

app = Flask(__name__)

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
upper = 0.0
lower = 0.0
fan = 0.0
time0 = time.time()
timei = 0.0

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
    # count = 0   # make this var a local

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
        # count = count + 1
        # print("Count %6d: top = %6.2f" % (count,top), flush=True)
        time.sleep(1)

#start up threads
t1 = threading.Thread(target=read_temps,daemon=True)
t1.start()

# flask webpage main
@app.route("/")
def index():
	return render_template('index3.html')

# flask web app that supplies data
@app.route('/chart_data')
def chart_data():
	def read_temps():
		while True:
			json_data = json.dumps(
				{'time':timei,\
				'top':top,'probe1':probe1,\
				'probe2':probe2,'back':back,\
				'pi':pi,'heatsink':heatsink,\
				'bottom':bottom,'front':front\
				})
			yield f"data:{json_data}\n\n"
			time.sleep(1)
	
	response = Response(stream_with_context(read_temps()), mimetype="text/event-stream")
	response.headers["Cache-Control"] = "no-cache"
	response.headers["X-Accel-Buffering"] = "no"
	return response
			
if __name__=="__main__":
	app.run(host='0.0.0.0',debug=False)






