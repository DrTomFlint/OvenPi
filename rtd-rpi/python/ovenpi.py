# ovenpi.py, try to read the rtds and show results on a formatted webpage
import librtd
import RPi.GPIO as GPIO
import time
import signal
from flask import Flask, render_template, request

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
# GPIO21 = Pin40 = Blue Wire = Upper Element
# GPIO16 = Pin36 = Yellow Wire = Fan
# GPIO12 = Pin32 = Green Wire = Lower Element
GPIO.setmode(GPIO.BCM)
GPIO.setup(21,GPIO.OUT)
GPIO.setup(16,GPIO.OUT)
GPIO.setup(12,GPIO.OUT)

# Create a dictionary to store temperatures
temps = {
	1:{'name':'top','value':0},
	2:{'name':'inside1','value':0},
	3:{'name':'inside2','value':0},
	4:{'name':'back','value':0},
	5:{'name':'pi','value':0},
	6:{'name':'heatsink','value':0},
	7:{'name':'bottom','value':0},
	8:{'name':'door','value':0}
}

@app.route("/")
def main():
	# read the 8 temperatures
	for temp in temps:
		temps[temp]['value']=round(librtd.get(0,temp),2)
	templateData = {
		'temps':temps
	}
	# pass template data to main.html
	return render_template('main.html',**templateData)
	
if __name__=="__main__":
	app.run(host='0.0.0.0',debug=True)






