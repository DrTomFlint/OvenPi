# Try to call into the library in a script.
import librtd
import RPi.GPIO as GPIO
import time
import signal

# Make Control C exit properly after turning off the SSRs
def handler(signum,frame):
	print(" ")
	print("Control C detected, exiting test3.py")
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

print("------------------------------------------------------------- ")
print("test3.py")
print("------------------------------------------------------------- ")
print(" ")

for i in range(50):
	temp1=librtd.get(0,1)
	temp2=librtd.get(0,2)
	temp3=librtd.get(0,3)
	temp4=librtd.get(0,4)
	temp5=librtd.get(0,5)
	temp6=librtd.get(0,6)
	temp7=librtd.get(0,7)
	temp8=librtd.get(0,8)
	print("Top    = %5.0f, Inside 1 = %5.0f, Inside 2 = %5.0f, Back = %5.0f" % (temp1,temp2,temp3,temp4))
	print("Bottom = %5.0f, Door     = %5.0f, Heatsink = %5.0f, Pi   = %5.0f" % (temp7,temp8,temp6,temp5))
	print(" ")

	if i == 5:
		print("Time is %d" % (i))
		print("Turn On Upper ")
		GPIO.output(21,1);

	if i == 10:
		print("Time is %d" % (i))
		print("Turn On Lower ")
		GPIO.output(12,1);

	if i == 15:
		print("Time is %d" % (i))
		print("Turn On Fan ")
		GPIO.output(16,1);

	if i == 35:
		print("Time is %d" % (i))
		print("Turn Off Fan ")
		GPIO.output(16,0);

	if i == 40:
		print("Time is %d" % (i))
		print("Turn Off Upper ")
		GPIO.output(21,0);

	if i == 45:
		print("Time is %d" % (i))
		print("Turn Off Lower ")
		GPIO.output(12,0);

	time.sleep(2.0)

GPIO.cleanup()





