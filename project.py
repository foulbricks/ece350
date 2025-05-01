import RPi.GPIO as GPIO  
import time
import requests
import json
import datetime

# spindle circumference in centimeters
circumf = 5.5

# will track the mode the curtain opener is on
modeCounter = 1

# will check if the curtain is open or closed
closed = True

# these will check at what time to close or open when setting a manual time
open_at = None
close_at = None

# distance to open curtains
distance = 0

# pins for stepper motor module
IN1 = 11     
IN2 = 12  
IN3 = 13  
IN4 = 15

# Button pins
modeBtn = 21    # the button that will change the mode
manualBtn = 22   # the button that will open or close the curtain in maual mode

seg_pins = [16,18,19,36,37,38,40] # pins corresponding to segments a b c d e f g in 7 seg display

# sample bits in the seven segment display, which will be converted to a hex
# number in the dats array. This are segments that need to be set         
#seg - gfe dcba
# 0  - 011 1111
# 1. - 000 0110
# 2 -  101 1011
# 3 -  100 1111
# 4 -  110 0110
# = [0,1,2,3,4,5,6,7,8,9,A,B,C]
dats = [0x3f,0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,0x7f,0x6f,0x77,0x7c,0x39]

# set up the pins for the motor module to output, the 7-segment pins to output and buttons as input
def setup():  
	GPIO.setwarnings(False)  
	GPIO.setmode(GPIO.BOARD)       # Numbers GPIOs by physical location  
	GPIO.setup(IN1, GPIO.OUT)      # Set pin's mode is output  
	GPIO.setup(IN2, GPIO.OUT)  
	GPIO.setup(IN3, GPIO.OUT)  
	GPIO.setup(IN4, GPIO.OUT)
	
	for pin in seg_pins:
		GPIO.setup(pin, GPIO.OUT)   # Set pin mode as output
		GPIO.output(pin, GPIO.LOW)
		
	GPIO.setup(modeBtn, GPIO.IN, pull_up_down=GPIO.PUD_UP)    # Set modeBtn's mode as input, and pull
	GPIO.setup(manualBtn, GPIO.IN, pull_up_down=GPIO.PUD_UP)    # Set manualBtn's mode as input, and pull
	# Callback to change the mode when a button is pressed
	GPIO.add_event_detect(modeBtn, GPIO.FALLING, callback=increment_mode_counter, bouncetime=200)
	
	
# It sets the steps on each row of the step motor
def setStep(w1, w2, w3, w4):  
	GPIO.output(IN1, w1)  
	GPIO.output(IN2, w2)  
	GPIO.output(IN3, w3)  
	GPIO.output(IN4, w4)

# resets the step motor rows
def stop():  
	setStep(0, 0, 0, 0)
	
# This will set the step motor to open the curtain
def open_curtain(delay, steps):
	for i in range(0, steps):  
		setStep(1, 0, 0, 1)  
		time.sleep(delay)  
		setStep(1, 1, 0, 0)  
		time.sleep(delay)  
		setStep(0, 1, 1, 0)  
		time.sleep(delay)  
		setStep(0, 0, 1, 1)  
		time.sleep(delay)

# This will set the step motor to close the curtain
def close_curtain(delay, steps):
	for i in range(0, steps):  
		setStep(0, 0, 1, 1)  
		time.sleep(delay)  
		setStep(0, 1, 1, 0)  
		time.sleep(delay)  
		setStep(1, 1, 0, 0)  
		time.sleep(delay)  
		setStep(1, 0, 0, 1)  
		time.sleep(delay)
		
# Sets the pin to HIGH if the binary representation of the decimal number is a 1
# or LOW if it is a zero
# writes a number 0-9 or a-f
def writeOneByte(val):
	GPIO.output(16, val & (0x01 << 0))  
	GPIO.output(18, val & (0x01 << 1))  
	GPIO.output(19, val & (0x01 << 2))  
	GPIO.output(36, val & (0x01 << 3))  
	GPIO.output(37, val & (0x01 << 4))  
	GPIO.output(38, val & (0x01 << 5))  
	GPIO.output(40, val & (0x01 << 6))


# Gets the sunset and sunrise times
def get_sunrise_sunset():
	currentDatetime = datetime.datetime.now()
	tomorrow = currentDatetime + datetime.timedelta(days=1)
	
	# URL to grab sunrise/sunset JSON data
	url = "https://api.sunrisesunset.io/json?lat=38.907192&lng=-77.036873&date=" + tomorrow.strftime("%Y-%m-%d")

	# make the request
	response = requests.get(url)

	# if the request was successful
	if response.status_code == 200:
		
		# get the response in JSON format
		json_data = response.json()
		
		# Convert the sunrise and sunset to a string
		sunrise_str = json_data["results"]["date"] + " " + json_data["results"]["sunrise"]
		sunset_str = json_data["results"]["date"] + " " + json_data["results"]["sunset"]
	
		# Convert the sunrise and sunset to a datetime object
		sunrise = datetime.datetime.strptime(sunrise_str, "%Y-%m-%d %I:%M:%S %p")
		sunset = datetime.datetime.strptime(sunset_str, "%Y-%m-%d %I:%M:%S %p")
		
		return sunrise, sunset
	# if request is unsuccessful print error, return None
	else:
		print(f"Error: { response.status_code }")
		return None, None

# Increment the modeCounter variable, loop between 1 and 3
def increment_mode_counter(channel):
	global modeCounter
	modeCounter = modeCounter + 1
	if modeCounter > 3:
		modeCounter = 1
	writeOneByte(dats[modeCounter])
		
# This will manually open and close the curtain on modeCounter 1
def manualOperation():
	global modeCounter
	global closed
	while modeCounter == 1:
		if GPIO.input(manualBtn) == GPIO.LOW:
			if closed:
				open_curtain(0.003, steps())
				closed = False
			else:
				close_curtain(0.003, steps())
				closed = True
				
# This will open and close the curtains at a certain time that was setup during initial setup
def manualOperationFromDate():
	global open_at
	global close_at
	global modeCounter
	global closed
	
	# When changing modes, it can happen that the time that the time to open or close was already expired, 
	# so set to the time to the next day if needed
	currentDatetime = datetime.datetime.now()
	
	if open_at is not None and currentDatetime > open_at:
		open_at = currentDatetime.replace(hour=int(open_at.strftime("%H")), minute=int(open_at.strftime("%M")), second=0)
		if currentDatetime > open_at:
			open_at = open_at + datetime.timedelta(days=1)
			
	if close_at is not None and currentDatetime > close_at:
		close_at = currentDatetime.replace(hour=int(open_at.strftime("%H")), minute=int(open_at.strftime("%M")), second=0)
		if currentDatetime > close_at:
			close_at = close_at + datetime.timedelta(days=1)
	
	if open_at is not None:
		print("Next opening at", open_at.strftime("%Y-%m-%d %I:%M:%S %p"))
	
	if close_at is not None:
		print("Next closing at", close_at.strftime("%Y-%m-%d %I:%M:%S %p"))
	
	while modeCounter == 2:
		# Check that open_at and close_at have been successfully set
		if not open_at is None and not close_at is None:
			currentDatetime = datetime.datetime.now()
			# If so, check that the current time is higher than when it should open
			# also make sure that the curtains are closed before opening them
			if currentDatetime > open_at and closed:
				open_curtain(0.003, steps())
				# set the curtain to open the next day
				open_at = open_at + datetime.timedelta(days=1)
				print("Next opening at", open_at.strftime("%Y-%m-%d %I:%M:%S %p"))
				closed = False
			# Check that the time to close the curtains has passed and the curtains are open
			elif currentDatetime > close_at and not closed:
				close_curtain(0.003, steps())
				# set the curtain to open the next day
				close_at = close_at + datetime.timedelta(days=1)
				print("Next closing at", open_at.strftime("%Y-%m-%d %I:%M:%S %p"))
				closed = True
			time.sleep(2)
				
# This will open the curtains at sunrise and close the curtains at sunset
def sunOperation():
	global modeCounter
	global closed
	sunrise, sunset = get_sunrise_sunset()
	print("The next sunrise is", sunrise.strftime("%Y-%m-%d %I:%M:%S %p"))
	print("The next sunset is", sunset.strftime("%Y-%m-%d %I:%M:%S %p"))
	
	while modeCounter == 3:
		currentDatetime = datetime.datetime.now()
		# Check that the sunrise has passed and the curtains are closed
		if currentDatetime > sunrise and closed:
			open_curtain(0.003, steps())
			# set the curtain to open at next sunrise
			sunrise, new_sunset = get_sunrise_sunset()
			print("Will open next at", sunrise.strftime("%Y-%m-%d %I:%M:%S %p"))
			closed = False
		# Check that the sunset has passed and the curtains are open
		elif currentDatetime > sunset and not closed:
			close_curtain(0.003, steps())
			# set the curtain to close at next sunrise
			new_sunrise, sunset = get_sunrise_sunset()
			print("Will close next at", sunset.strftime("%Y-%m-%d %I:%M:%S %p"))
			closed = True
		time.sleep(2)
			
# Indicates to the program if the curtains are initially closed or open	
def setInitialState():
	global closed
	while True:
		print("Please enter if the curtain is currently `open` or `closed`")
		state = input()
		if state == "open" or state == "closed":
			break
		else:
			print("Invalid input")
			
	if state == "open":
		closed = False
	elif state == "closed":
		closed = True
		
# Converts the user input at initial setup to a datetime object
def timeStrToDatetime(input_str):
	if input_str == "0":
		return None
	else:
		d = datetime.datetime.now()
		d = d.replace(hour=int(input_str[0:2]), minute=int(input_str[3:5]), second=int(input_str[6:8]))
		if datetime.datetime.now() > d:
			d = d + datetime.timedelta(days=1)
		return d

def steps():
	return int(distance / circumf * 512)
		
if __name__ == "__main__":
	try:
		setup()
		print("Initial Setup")
		setInitialState()
		
		print("Please enter the width of the curtain in centimeters")
		distance = int(input())
		
		print("Please enter an optional time to open the curtains every day in the format HH:MM:SS")
		print("Enter 0 if you would not like it to be set")
		open_at_str = input()
		open_at = timeStrToDatetime(open_at_str)
		
		print("Please enter an optional time to close the curtains every day in the format HH:MM:SS")
		print("Enter 0 if you would not like it to be set")
		close_at_str = input()
		close_at = timeStrToDatetime(close_at_str)
		
		# Write mode initially
		writeOneByte(dats[modeCounter])
		
		while True:
			if modeCounter == 1:
				manualOperation()
			elif modeCounter == 2:
				manualOperationFromDate()
			elif modeCounter == 3:
				sunOperation()
		
	except KeyboardInterrupt:
		for pin in seg_pins:
			GPIO.output(pin, GPIO.LOW)
			
		GPIO.cleanup()

	