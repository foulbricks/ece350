# 4-digit 7-segment display pin configuration
SEGMENT_PINS = [None] * 7  # a, b, c, d, e, f, g
DIGIT_PINS = [None] * 4    # D1, D2, D3, D4 (digit control lines)

for pin in SEGMENT_PINS:
	if pin is not None:
		GPIO.setup(pin, GPIO.OUT)
		GPIO.output(pin, GPIO.LOW)

for pin in DIGIT_PINS:
	if pin is not None:
		GPIO.setup(pin, GPIO.OUT)
		GPIO.output(pin, GPIO.LOW)

def display_digit(digit, value):
	# Turn off all digits
	for d in DIGIT_PINS:
		GPIO.output(d, GPIO.LOW)
	
	# Set segment bits for the current value (0-F)
	byte = dats[value]
	for i in range(7):
		if SEGMENT_PINS[i] is not None:
			GPIO.output(SEGMENT_PINS[i], GPIO.HIGH if (byte >> i) & 1 else GPIO.LOW)

	# Turn on the selected digit
	if DIGIT_PINS[digit] is not None:
		GPIO.output(DIGIT_PINS[digit], GPIO.HIGH)

# Display the time in HHMM format
def display_time(hour, minute, duration=5):
	end_time = time.time() + duration
	h = f"{hour:02d}"
	m = f"{minute:02d}"
	digits = [int(h[0]), int(h[1]), int(m[0]), int(m[1])]
	
	while time.time() < end_time:
		for i in range(4):
			display_digit(i, digits[i])
			time.sleep(0.005)

def sunOperation():
	global modeCounter
	global closed
	sunrise, sunset = get_sunrise_sunset()
	
	if sunrise:
		print("The next sunrise is", sunrise.strftime("%Y-%m-%d %I:%M:%S %p"))
		hour = sunrise.hour
		minute = sunrise.minute
		display_time(hour, minute)  # <-- display the time for 5 seconds

	if sunset:
		print("The next sunset is", sunset.strftime("%Y-%m-%d %I:%M:%S %p"))
	
	while modeCounter == 3:
		currentDatetime = datetime.datetime.now()
		if currentDatetime > sunrise and closed:
			open_curtain(0.003, steps())
			sunrise, new_sunset = get_sunrise_sunset()
			if sunrise:
				display_time(sunrise.hour, sunrise.minute)
				print("Will open next at", sunrise.strftime("%Y-%m-%d %I:%M:%S %p"))
			closed = False
		elif currentDatetime > sunset and not closed:
			close_curtain(0.003, steps())
			new_sunrise, sunset = get_sunrise_sunset()
			if sunset:
				print("Will close next at", sunset.strftime("%Y-%m-%d %I:%M:%S %p"))
			closed = True
		time.sleep(2)
