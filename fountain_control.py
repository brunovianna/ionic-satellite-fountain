
""" 
pass data: satname, aos time, aos azimuth, tca time, tca elevation, tca azimuth, eos time, eos azimuth
pass detail data: time, azimuth, elevation

using the isf ardruino control library
// fountain control
// outputs 2-7 control the servos
// outputs 8-13 control the pump switches
// pump 1 -- pin 2 (servo), pin 8 (switch) -- and son on

// serial protocol
// first char d (for digital), 2nd and 3rd chars the pin (ex 10), 4th char state (1 or 0)
// or
// first char s (for servo), 2nd and 3rd chars the pin (ex 03), 4th, 5th, 6th the angle (ex 070)
//
// examples:
// d051 - turn on nozzle 5 
// s03080 - turn servo 3  to 80 degress

// pin mapping

arduino 2 - servo 2 (1)
arduino 3 - servo 1 (0)
arduino 4 - servo 4 (3)
arduino 5 - servo 3 (2)
arduino 6 - servo 6 (5)
arduino 7 - servo 5 (4)
arduino 8 - bomba 2
arduino 9 - bomba 1
arduino 10 - bomba 4
arduino 11 - bomba 3
arduino 12 - bomba 6
arduino 13 - bomba 5




"""


from simpleOSC import *
import time, sys, select, threading, serial, OSC

global index_pass, current_pass,IS_JUST_A_TEST

class fountain_pass:
    def __init__(self, sat, start_time, end_time, tca_el, details):
        self.sat = sat
        self.start_time = start_time
        self.end_time = end_time
        self.tca_el = tca_el
        self.details = details

class sat:
	def __init__(self, name, freq, band):	
		self.name = name
		self.freq = freq
		self.band = band


class sat_pass:
	def __init__(self, sat, aos, aos_az, tca, tca_az, tca_el, eos, eos_az):
		self.sat = sat
		self.aos = aos
		self.aos_az = aos_az
		self.tca = tca
		self.tca_az = tca_az
		self.tca_el = tca_el
		self.eos = eos
		self.eos_az = eos_az
		self.details = []

	def add_detail(self,d):
		self.details.append(d)

class pass_detail:
    def __init__(self, time, az, el, range_rate):
        self.time = time
        self.az=az
        self.el=el
        self.range_rate=range_rate




# define a message-handler function for the server to call.
def pass_handler(addr, tags, data, source):
    global index_pass
    """
    print "received new osc msg from %s" % getUrlStr(source)
    print "with addr : %s" % addr
    print "typetags : %s" % tags
    print "the actual data is :%s" % data
    print "data :%s" % data[1]
    #print "converted data :%s" % t
    print "the time :%s" % time.ctime(data[1])
    print "---"

        """
    s = find_sat(data[0]) 
    
    if (s == -1):
        
        s = sat(data[0],0,0)
        sats.append(s)

    
    p = sat_pass(s, data[1],data[2], data[3], data[4], data[5], data[6], data[7])
    sat_passes.append(p)
    index_pass = p

def start_passes_handler(addr, tags, data, source):
    #don't let the update passes access pass data while we're updating it
    semaphore.acquire()
    sat_passes = []

def done_passes_handler(addr, tags, data, source):
    #now it can access
    semaphore.release()
    #only in the first time --- on the others, let the main loop decide when to update
    if next_pass == None:
        update_fountain_schedule()
    
def detail_handler(addr, tags, data, source):
    global index_pass
    d = pass_detail(data[0], data[1], data[2], data[3] / 100)
    if (index_pass == -1):
        print "no pass? bug"
    else:
        index_pass.add_detail(d)
   
# define a message-handler function for the server to call.
def nothing_handler(addr, tags, data, source):
    if (1==0):
        print "-"


def find_sat(name):
    for sat in sats:
        if (sat.name == name):
            return sat
            break
    return -1

def heard_enter():
    i,o,e = select.select([sys.stdin],[],[],0.0001)
    for s in i:
        if s == sys.stdin:
            input = sys.stdin.readline()
            return True
    return False

def print_passes(sp):
    for p in sp:
        print p.sat.name
        print "AOS time: %s, max el: %s" % (time.ctime(p.aos), p.tca_el)
        for d in p.details:
            print "detail: %s %s %s" %(time.ctime(d.time), d.az, d.el)

def print_schedule(fp):
    for p in fp:
        print "name: %s, start: %s, end: %s, elevation: %s" % (p.sat.name, time.ctime(p.start_time), time.ctime(p.end_time), p.tca_el)

def print_next_pass():
    if next_pass == None:
        print "no data yet"
    else:
        print next_pass.sat.name
        for d in next_pass.details:
            print " %s, az: %s, el: %s" % (get_str_time(d.time), d.az, d.el)

def update_fountain_schedule():
    global next_pass
    semaphore.acquire()
    sp = sorted(sat_passes, key=lambda sat_pass: sat_pass.tca_el, reverse=True)
    semaphore.release()
    for p in sp:
        #laboral only:
        #discard passes that begin AND end on the west side of the sky
        if (p.aos_az < 180) or (p.eos_az < 180):            
            if fountain_passes == []:
                fp = fountain_pass(p.sat, p.aos, p.eos, p.tca_el, p.details)
                fountain_passes.append(fp)
            else:
                #fp is the last pass to be added to the schedule
                
                #now check against all previous passes if there's anything else at the same time
                pass_ok = True
                for cp in fountain_passes:
                    #plus 5 seconds before and after - this will be the time to resettle the nozzles
                    if ((p.aos >= cp.start_time-5) and (p.aos <= cp.end_time+5)) or ((p.eos>=cp.start_time-5) and (p.eos<=cp.end_time+5)):
                        pass_ok = False
                        break
                if pass_ok == True:
                    
                    new_details = []
                    for nd in p.details:
                        #laboral only:
                        #we don't want the event details that happen in the west part of the sky (> 180 deg azimuth)
                        #we don't want event details too close to the horizon (10 deg elevation minimun)
                        if (nd.az < 180) and (nd.el >= 10):
                            new_details.append(nd)
                    
                    fp = fountain_pass(p.sat, p.aos, p.eos, p.tca_el, new_details)
                    fountain_passes.append(fp)
             
    fountain_passes.sort(key=lambda fountain_pass: fountain_pass.start_time)
    
    for fp in fountain_passes:
        #print "my time %s, start %s" % (time.ctime(my_get_time()), time.ctime(fp.start_time))
        if my_get_time() < fp.start_time - 5:
            next_pass = fp
            break

   

def find_best_nozzle (az):
    global nozzles_azimuth
    min_diff = 1000
    best = -1
    for n in nozzles_azimuth:
        if abs(az - n) < min_diff:
            min_diff = abs(az-n)
            best = nozzles_azimuth.index(n)
    return (best)

def find_servo_angle(a):
    #not ready yeat
    return a

def my_get_time():
    #for debug purposes
    return int(time.mktime(time.localtime()))

def get_str_time(t=my_get_time()): 
    return time.strftime("%H:%M:%S", time.localtime(t))

#string

def add_zeros_100 (a):
    if a < 10:
        add_zeros = "00"
    elif a< 100:
        add_zeros = "0"
    else:
        add_zeros = ""
    return str(add_zeros)+str(a)

def add_zeros_10 (a):
    if a < 10:
        add_zeros = "0"
    else:
        add_zeros = ""
    return str(add_zeros)+str(a)

#nozzle controls

def nozzle_solo(n):
    nnn = []
    for i in range(len(nozzles_azimuth)):
        if (i==n):
            nnn.append(1)
        else:
            nnn.append(0)
    if IS_JUST_A_TEST:
        print "nozzles state %s command %s" % nnn,
    else:
        for i in range(len(nnn)):
            str = "d"+add_zeros_10(i)+nnn[i]+"\n"
            arduino.write(str)

def move_nozzle(n,a):
    str = "s"+add_zeros_10(n)+add_zeros_100(a)+"\n"
    if IS_JUST_A_TEST:
        print "angle %s command %s" % ( a)
    else:
        arduino.write(str)
	pins[n] = a

def go_slow(pin, angle, delta, interval):
  if pins[pin] > angle:
    while (pins[pin]-delta > angle):
      pins[pin]=(pins[pin]-delta)
      str = "s"+add_zeros_10(pin)+add_zeros_100(pins[pin]-delta)+"\n"
      arduino.write(str)
      time.sleep(interval)
  else:
      while (pins[pin]+delta < angle):
        pins[pin]=(pins[pin]+delta)
        str = "s"+add_zeros_10(pin)+add_zeros_100(pins[pin]+delta)+"\n"
        arduino.write(str)
        time.sleep(interval)

#oled draw

def dec2hex(n):
	"""return the hexadecimal string representation of integer n"""
	return "%X" % n
 
def hex2dec(s):
	"""return the integer value of a hexadecimal string s"""
	return int(s, 16)
 
def send_sgc_commands(commands):
	global arduino, oled
	if type(commands)==type(str()):
		for command in commands.split(","):
			command = hex2dec(command)
			if command < 0:
				command = 0
			if command > 255:
				command = 255			
			oled.write(chr(command))
	elif type(commands)==type(list()):
		for command in commands:
			if type(command)==type(str()):
				command = hex2dec(command)
			if command < 0:
				command = 0
			if command > 255:
				command = 255			
			oled.write(chr(command))

def sgc_print(x,y,font,color_1,color_2, w, h, text):
	global arduino, oled
	print "text= ", text
	oled.write("S")
	oled.write(chr(x))
	oled.write(chr(y))
	oled.write(chr(font))
	oled.write(chr(color_1))
	oled.write(chr(color_2))
	oled.write(chr(w))
	oled.write(chr(h))
	for c in text:
		oled.write(c)
	oled.write(chr(0))


def draw_sat(x,y):
	#print x,y
	send_sgc_commands(["72",x,y,x+40,y+20,0,31]) #rectangle
	print "ds rec 1"
	ack_or_reset()
	send_sgc_commands(["4C",x+40,y+10,x+44,y+10,0,31]) #line
	print "ds line 1"
	ack_or_reset()
	send_sgc_commands(["43",x+60,y+10,15,0,31]) #circle
	print "ds circle"
	ack_or_reset()
	send_sgc_commands(["4C",x+75,y+10,x+80,y+10,0,31]) #line
	print "ds line 2"
	ack_or_reset()
	send_sgc_commands(["72",x+80,y,x+120,y+20,0,31]) #rectangle
	print "ds rec 2"
	ack_or_reset()
	
def reset_or_die():
	time.sleep(0.5)
	print "trying to reset..."
	oled.write("U")
	ack=oled.read(1)
	if len(ack)==0:
		ack ="!"

	tries = 0
	while ord(ack)!=6:
		time.sleep(0.5)
		print "trying to reset..."
		oled.write("U")
		ack=oled.read(1)
		if len(ack)==0:
			ack ="!"
		tries = tries + 1


	oled.write("E")
	ack=oled.read(1)


def ack_or_reset():
	global arduino, oled

	ack=oled.read(1)
	if (len(ack))==0:
		print "time out exit"
		oled.write("U")
		ack=oled.read(1)
		#sys.exit()
		#reset_or_die()
	elif ord(ack) != 6:
		print "bad ack exit"
		#sys.exit()		
		#reset_or_die()
		

def update_oled (satname, timetext):

	global oled_sat_pos, now_blink
	global arduino, oled

	oled.write("E") #clear screen
	ack_or_reset()

	satname = satname[0:10] #clip if too long

	send_sgc_commands(["70",01]) #no fill
	print "no fill"
	ack_or_reset()
	send_sgc_commands(["72",00,00,159,12,255,255]) #rectangle
	print "rect title"
	ack_or_reset()
	send_sgc_commands(["70",0]) # fill
	ack_or_reset()
	
	oled_sat_pos = oled_sat_pos + 4
	if (oled_sat_pos == 160):
		oled_sat_pos = 0

	draw_sat(oled_sat_pos,26)
	send_sgc_commands(["70",01]) #no fill
	print "no fill"
	ack_or_reset()
	sgc_print(7,2,0,248,0,1,1,"ionic satellite fountain")
	print "title"
	ack_or_reset()
	sgc_print(0,68,2,255,255,1,1,"next pass:")
	print "next pass"
	ack_or_reset()
	sgc_print(0,83,2,255,255,2,2,satname)
	print "sat name"
	ack_or_reset()
	if timetext == "now!":
		if now_blink == True:
			sgc_print(0,110,0,255,255,2,2,timetext)
			now_blink = False
		else:
			now_blink == True
	else:
		sgc_print(0,110,0,255,255,2,2,timetext)
	
	print "time"
	#sgc_print(20,110,0,227,156,2,2,"in 2:10:10")
	ack_or_reset()

#serial ports

def open_serials():
	global arduino, oled

	s1 = None
	s2 = None

	
	try:
		s1 = serial.Serial ("/dev/ttyUSB0",9600, timeout=1)
	
	except:
		print "serial port /dev/ttyUSB0 not found"
		sys.exit()

	
	try:
		s2 = serial.Serial ("/dev/ttyUSB1", 9600, timeout=1)
	
	except:
		print "serial port /dev/ttyUSB1 not found"
		sys.exit()

	s1.open()
	s1.write("U")	
	ack = s1.read(1)
	if len(ack) > 0:
		if ack == "A":
			arduino = s1
			oled = s2
			oled.write("U")
			ack = oled.read(1)
			if len(ack) == 0:
				print "oled problem - timeout", ack
				sys.exit()
			if ord(ack) != 6:
				print "oled problem - bad ack", ack
				sys.exit()
			oled.timeout = None
			oled.write("U") #set baud rate
			ack_or_reset()
			oled.write("E") #clear screen
			ack_or_reset()
			arduino.timeout = 0.1
			print "arduino on USB0"
			print "oled on USB1"

		elif ord(ack) == 6:
			arduino = s2
			oled = s1
			arduino.timeout = 0.1
			arduino.write("U")
			ack = arduino.read(1)
			if ack != "A":
				print "arduino not connected"
				sys.exit()
			oled.timeout = 5
			oled.write("U") #set baud rate
			ack_or_reset()
			oled.write("E") #clear screen
			ack_or_reset()
			print "arduino on USB1"
			print "oled on USB0"
		else:
			print "?"

	else:
		print "something is wrong :-O "
		print "try again in a few seconds "
		print "if still not working reconnect the cables"
		sys.exit()

IS_JUST_A_TEST = False


arduino = oled = None

oled_sat_pos = 0



if IS_JUST_A_TEST is False: 	
	open_serials()	


index_pass = -1  
current_pass = None
next_pass = None

semaphore = threading.BoundedSemaphore()

initOSCServer('127.0.0.1', 7771)


sats = []
sat_passes = []
fountain_passes = []

#laboral is inclined 8deg to true north
#first nozzle at 15deg from building alignment, ie 23deg
#the others 30deg spaced
nozzles_azimuth = [23, 53,83, 113, 143, 173] 





pins = [0,0,0,0,0,0]

setOSCHandler("/gpredict/sats/all", nothing_handler) # adding our function
setOSCHandler("/gpredict/sat/", nothing_handler) # adding our function
setOSCHandler("/gpredict/sat/next", nothing_handler) # adding our function
setOSCHandler("/gpredict/sats/next", nothing_handler) # adding our function
setOSCHandler("/gpredict/sats", nothing_handler) # adding our function
setOSCHandler("/gpredict/pass", pass_handler) # adding our function
setOSCHandler("/gpredict/pass/detail", detail_handler) # adding our function
setOSCHandler("/gpredict/pass/start", start_passes_handler) # adding our function
setOSCHandler("/gpredict/pass/done", done_passes_handler) # adding our function


# just checking which handlers we have added. not really needed
reportOSCHandlers()



try :
    while 1 :
        time.sleep(1)
        
        #check if we got info from gpredict yet
        if (next_pass != None) and (oled != None) and (arduino != None):
            print "n %s s: %s, e %s" % (get_str_time(my_get_time()), get_str_time(next_pass.start_time), get_str_time(next_pass.end_time)),
            if (my_get_time() >= next_pass.start_time - 5) and (my_get_time() < next_pass.start_time):
                #next pass will be within 5 secs
                #print "soon - next start: %s, next end %s" % (time.ctime(next_pass.start_time), time.ctime(next_pass.end_time))
                print " soon "
            elif (my_get_time() >= next_pass.start_time) and (my_get_time() < next_pass.end_time):
                #next pass is NOW!
                last_time = next_pass.end_time
                
                details_now = None
                for d in next_pass.details:
                    if (my_get_time() >= d.time):
                        details_now = d
                    else:
                        break
                
                print "now: az: %s el: %s" % ( d.az, d.el),
                
                n = find_best_nozzle(d.az)
                a = find_servo_angle(d.el)
                
                nozzle_solo(n)
                move_nozzle(n,a)
		update_oled (next_pass.sat.name, "now!")
                print ""

            else:
                #no activity - go ahead and update the schedule
                print "else"
                update_fountain_schedule()
		update_oled (next_pass.sat.name, "in "+get_str_time(next_pass.start_time-my_get_time()))

        #to check, press enter at the terminal
        if heard_enter():
            #print_passes(sat_passes)
            #update_fountain_schedule()
            print_schedule(fountain_passes)
            print_next_pass()

except KeyboardInterrupt :
    print "\nClosing OSCServer."
    print "Waiting for Server-thread to finish"
    closeOSC()
    print "Done"
        


