# ovenpi.py, try to read the rtds and show results on a formatted webpage
import librtd
import RPi.GPIO as GPIO
import time
import signal
import json
from datetime import datetime
from flask import Flask, Response, render_template, stream_with_context

app = Flask(__name__)

# # Make Control C exit properly after turning off the SSRs
# def handler(signum,frame):
# 	print(" ")
# 	print("Control C detected, exiting ovenpi.py")
# 	print(" ")
# 	GPIO.output(21,0)
# 	GPIO.output(16,0)
# 	GPIO.output(12,0)
# 	GPIO.cleanup()
# 	exit(1)

# signal.signal(signal.SIGINT, handler)
	
# # Setup GPIOs that control the SSRs
# # GPIO21 = Pin40 = Blue Wire = Upper Element
# # GPIO16 = Pin36 = Yellow Wire = Fan
# # GPIO12 = Pin32 = Green Wire = Lower Element
# GPIO.setmode(GPIO.BCM)
# GPIO.setup(21,GPIO.OUT)
# GPIO.setup(16,GPIO.OUT)
# GPIO.setup(12,GPIO.OUT)

# # Create a dictionary to store temperatures
# temps = {
# 	1:{'name':'top','value':0},
# 	2:{'name':'inside1','value':0},
# 	3:{'name':'inside2','value':0},
# 	4:{'name':'back','value':0},
# 	5:{'name':'pi','value':0},
# 	6:{'name':'heatsink','value':0},
# 	7:{'name':'bottom','value':0},
# 	8:{'name':'front','value':0}
# }

@app.route("/")
def index():
	return render_template('index.html')

@app.route('/chart_data')
def chart_data():
	def read_temps():
		while True:
			json_data = json.dumps(
				{'time':datetime.now().strftime('%H:%M:%S'),\
				'top':round(librtd.get(0,1),2),'probe1':round(librtd.get(0,2),2),\
				'probe2':round(librtd.get(0,3),2),'back':round(librtd.get(0,4),2),\
				'pi':round(librtd.get(0,5),2),'heatsink':round(librtd.get(0,6),2),\
				'bottom':round(librtd.get(0,7),2),'front':round(librtd.get(0,8),2)
				})
			yield f"data:{json_data}\n\n"
			time.sleep(1)
	
	response = Response(stream_with_context(read_temps()), mimetype="text/event-stream")
	response.headers["Cache-Control"] = "no-cache"
	response.headers["X-Accel-Buffering"] = "no"
	return response
			
if __name__=="__main__":
	app.run(host='0.0.0.0',debug=True)






