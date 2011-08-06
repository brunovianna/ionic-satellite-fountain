
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
import time, sys, select, threading, serial, OSC, string

from gnuradio import audio
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio import blks2
from gnuradio.eng_option import eng_option
from gnuradio.gr import firdes

import fcd


global index_pass, current_pass,IS_JUST_A_TEST


# fm receiver, created using gnuradio-companion
class fm_rx(gr.top_block):

	def __init__(self):
		gr.top_block.__init__(self, "FM Receiver")

		##################################################
		# Variables
		##################################################
		self.samp_rate = samp_rate = 96000
		self.xlate_filter_taps = xlate_filter_taps = firdes.low_pass(1, samp_rate, 48000, 5000, firdes.WIN_HAMMING, 6.76)
		self.sql_lev = sql_lev = -100
		self.rf_gain = rf_gain = 20
		self.freq = freq = 144800000
		self.af_gain = af_gain = 2

		##################################################
		# Blocks
		##################################################
		self.xlating_fir_filter = gr.freq_xlating_fir_filter_ccc(1, (xlate_filter_taps), 0, samp_rate)
		self.nbfm_normal = blks2.nbfm_rx(
			audio_rate=48000,
			quad_rate=96000,
			tau=75e-6,
			max_dev=5e3,
		)
		self.low_pass_filter = gr.fir_filter_ccf(1, firdes.low_pass(
			1, samp_rate, 12500, 1500, firdes.WIN_HAMMING, 6.76))
		self.gr_simple_squelch_cc_0 = gr.simple_squelch_cc(sql_lev, 1)
		self.gr_multiply_const_vxx_1 = gr.multiply_const_vff((af_gain, ))
		self.fcd_source_c_1 = fcd.source_c("hw:1")
		self.fcd_source_c_1.set_freq(freq)
		self.fcd_source_c_1.set_freq_corr(-32)
		    
		self.audio_sink = audio.sink(48000, "", True)

		##################################################
		# Connections
		##################################################
		self.connect((self.xlating_fir_filter, 0), (self.low_pass_filter, 0))
		self.connect((self.low_pass_filter, 0), (self.gr_simple_squelch_cc_0, 0))
		self.connect((self.gr_multiply_const_vxx_1, 0), (self.audio_sink, 1))
		self.connect((self.gr_multiply_const_vxx_1, 0), (self.audio_sink, 0))
		self.connect((self.gr_simple_squelch_cc_0, 0), (self.nbfm_normal, 0))
		self.connect((self.nbfm_normal, 0), (self.gr_multiply_const_vxx_1, 0))
		self.connect((self.fcd_source_c_1, 0), (self.xlating_fir_filter, 0))

	def get_samp_rate(self):
		return self.samp_rate

	def set_samp_rate(self, samp_rate):
		self.samp_rate = samp_rate
		self.set_xlate_filter_taps(firdes.low_pass(1, self.samp_rate, 48000, 5000, firdes.WIN_HAMMING, 6.76))
		self.low_pass_filter.set_taps(firdes.low_pass(1, self.samp_rate, 12500, 1500, firdes.WIN_HAMMING, 6.76))

	def get_xlate_filter_taps(self):
		return self.xlate_filter_taps

	def set_xlate_filter_taps(self, xlate_filter_taps):
		self.xlate_filter_taps = xlate_filter_taps
		self.xlating_fir_filter.set_taps((self.xlate_filter_taps))

	def get_sql_lev(self):
		return self.sql_lev

	def set_sql_lev(self, sql_lev):
		self.sql_lev = sql_lev
		self.gr_simple_squelch_cc_0.set_threshold(self.sql_lev)

	def get_rf_gain(self):
		return self.rf_gain

	def set_rf_gain(self, rf_gain):
		self.rf_gain = rf_gain
		self.fcd_source_c_1.set_lna_gain(self.rf_gain)

	def get_freq(self):
		return self.freq

	def set_freq(self, freq):
		self.freq = freq
		self.fcd_source_c_1.set_freq(self.freq)

	def get_af_gain(self):
		return self.af_gain

	def set_af_gain(self, af_gain):
		self.af_gain = af_gain
		self.gr_multiply_const_vxx_1.set_k((self.af_gain, ))

# cw / ssb receiver (just change bandpass filter values), created using gnuradio-companion
class cw_rx(gr.top_block):

	def __init__(self):
		gr.top_block.__init__(self, "CW/SSB Receiver")

		##################################################
		# Variables
		##################################################
		self.samp_rate = samp_rate = 96000
		self.xlate_filter_taps = xlate_filter_taps = firdes.low_pass(1, samp_rate, 48000, 5000, firdes.WIN_HAMMING, 6.76)
		self.sql_lev = sql_lev = -100
		self.rf_gain = rf_gain = 20
		self.pass_trans = pass_trans = 600
		self.pass_low = pass_low = 300
		self.pass_high = pass_high = 1200
		self.freq = freq = 144800000
		self.af_gain = af_gain = 5

		##################################################
		# Blocks
		##################################################
		self.xlating_fir_filter = gr.freq_xlating_fir_filter_ccc(1, (xlate_filter_taps), 0, samp_rate)
		self.gr_simple_squelch_cc_0 = gr.simple_squelch_cc(sql_lev, 1)
		self.gr_multiply_const_vxx_0 = gr.multiply_const_vff((af_gain, ))
		self.gr_complex_to_real_0 = gr.complex_to_real(1)
		self.gr_agc2_xx_0 = gr.agc2_cc(1e-1, 20.8e-6, 0.3, 1.0, 0.0)
		self.fcd_source_c_1 = fcd.source_c("hw:1")
		self.fcd_source_c_1.set_freq(freq)
		self.fcd_source_c_1.set_freq_corr(-10)
		    
		self.band_pass_filter_0 = gr.fir_filter_ccf(2, firdes.band_pass(
			1, samp_rate, pass_low, pass_high, pass_trans, firdes.WIN_HAMMING, 6.76))
		self.audio_sink = audio.sink(48000, "", True)

		##################################################
		# Connections
		##################################################
		self.connect((self.fcd_source_c_1, 0), (self.xlating_fir_filter, 0))
		self.connect((self.xlating_fir_filter, 0), (self.gr_simple_squelch_cc_0, 0))
		self.connect((self.band_pass_filter_0, 0), (self.gr_agc2_xx_0, 0))
		self.connect((self.gr_complex_to_real_0, 0), (self.gr_multiply_const_vxx_0, 0))
		self.connect((self.gr_agc2_xx_0, 0), (self.gr_complex_to_real_0, 0))
		self.connect((self.gr_simple_squelch_cc_0, 0), (self.band_pass_filter_0, 0))
		self.connect((self.gr_multiply_const_vxx_0, 0), (self.audio_sink, 0))
		self.connect((self.gr_multiply_const_vxx_0, 0), (self.audio_sink, 1))

	def get_samp_rate(self):
		return self.samp_rate

	def set_samp_rate(self, samp_rate):
		self.samp_rate = samp_rate
		self.set_xlate_filter_taps(firdes.low_pass(1, self.samp_rate, 48000, 5000, firdes.WIN_HAMMING, 6.76))
		self.band_pass_filter_0.set_taps(firdes.band_pass(1, self.samp_rate, self.pass_low, self.pass_high, self.pass_trans, firdes.WIN_HAMMING, 6.76))

	def get_xlate_filter_taps(self):
		return self.xlate_filter_taps

	def set_xlate_filter_taps(self, xlate_filter_taps):
		self.xlate_filter_taps = xlate_filter_taps
		self.xlating_fir_filter.set_taps((self.xlate_filter_taps))

	def get_sql_lev(self):
		return self.sql_lev

	def set_sql_lev(self, sql_lev):
		self.sql_lev = sql_lev
		self.gr_simple_squelch_cc_0.set_threshold(self.sql_lev)

	def get_rf_gain(self):
		return self.rf_gain

	def set_rf_gain(self, rf_gain):
		self.rf_gain = rf_gain
		self.fcd_source_c_1.set_lna_gain(self.rf_gain)

	def get_pass_trans(self):
		return self.pass_trans

	def set_pass_trans(self, pass_trans):
		self.pass_trans = pass_trans
		self.band_pass_filter_0.set_taps(firdes.band_pass(1, self.samp_rate, self.pass_low, self.pass_high, self.pass_trans, firdes.WIN_HAMMING, 6.76))

	def get_pass_low(self):
		return self.pass_low

	def set_pass_low(self, pass_low):
		self.pass_low = pass_low
		self.band_pass_filter_0.set_taps(firdes.band_pass(1, self.samp_rate, self.pass_low, self.pass_high, self.pass_trans, firdes.WIN_HAMMING, 6.76))

	def get_pass_high(self):
		return self.pass_high

	def set_pass_high(self, pass_high):
		self.pass_high = pass_high
		self.band_pass_filter_0.set_taps(firdes.band_pass(1, self.samp_rate, self.pass_low, self.pass_high, self.pass_trans, firdes.WIN_HAMMING, 6.76))

	def get_freq(self):
		return self.freq

	def set_freq(self, freq):
		self.freq = freq
		self.fcd_source_c_1.set_freq(self.freq)

	def get_af_gain(self):
		return self.af_gain

	def set_af_gain(self, af_gain):
		self.af_gain = af_gain
		self.gr_multiply_const_vxx_0.set_k((self.af_gain, ))


class spawn_rx(threading.Thread):
	# select rx mode
	def __init__(self):  
		threading.Thread.__init__(self)  
		self.status = "stopped"


	def start_rx(self, mode, freq):
		self.mode = mode
		self.freq = freq
		

		if not IS_JUST_A_TEST:
			if mode == 'cw': 
				self.rx = cw_rx()

			if mode == 'fm':
				self.rx = fm_rx()

			self.rx.set_freq(self.freq)
			self.rx.start()
		self.status = "running"

	def stop_rx(self):
		if not IS_JUST_A_TEST:
			self.rx.stop()
			del self.rx
		self.status = "stopped"

	def set_freq(self, freq):
		self.freq=freq
		if not IS_JUST_A_TEST:
			self.rx.set_freq(freq)

#data classes

class fountain_pass:
	def __init__(self, sat, start_time, end_time, tca_el, details):
		self.sat = sat
		self.start_time = start_time
		self.end_time = end_time
		self.tca_el = tca_el
		self.details = details

class sat:
	def __init__(self, name, freq, mode):	
		self.name = name
		self.freq = freq
		self.mode = mode


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
	def __init__(self, time, az, el, doppler):
		self.time = time
		self.az=az
		self.el=el
		self.doppler=doppler




# define a message-handler function for the server to call.
def pass_handler(addr, tags, data, source):
	global index_pass, sats, sat_passes

	semaphore.acquire()

	name = data[0]

	s = find_sat(name)

	if (s == -1):
		
		found = False

		for i in sat_data:
			if (i['name'])==name:
				found = True 
				fr = i['freq']
				mode = i['mode']
		
		if not found:
			print "couldn't find satellite radio data for "+name
			for l in name:
				print ord(l), " ",
		else:
			s = sat(name,fr,mode)
			sats.append(s)

	p = sat_pass(s, data[1],data[2], data[3], data[4], data[5], data[6], data[7])

	if not (find_sat_pass(s.name, data[1])):
		sat_passes.append(p)

	index_pass = p
	semaphore.release()

	#print "name %s, details %s %s %s %s", index_pass.sat.name, data[1], data[2], len(sat_passes)

def start_passes_handler(addr, tags, data, source):
	global sat_passes

	#don't let the update passes access pass data while we're updating it
	#sat_passes = []

def done_passes_handler(addr, tags, data, source):
	#now it can access
	#only in the first time --- on the others, let the main loop decide when to update
	if next_pass == None:
		update_fountain_schedule()

def detail_handler(addr, tags, data, source):
	global index_pass
	d = pass_detail(data[0], data[1], data[2], data[3])
	if (index_pass == -1):
		print "no pass? bug"
	else:
		index_pass.add_detail(d)

	#print "name %s, details %s %s %s %s", index_pass.sat.name, data[0], data[1], data[2], data[3] / 100

# define a message-handler function for the server to call.
def nothing_handler(addr, tags, data, source):
	if (1==0):
		print "-"

def find_sat_pass(name, aos):
	global sat_passes
	for sat_pass in sat_passes:
		if (sat_pass.sat.name == name) and (sat_pass.aos >= aos - 120) and (sat_pass.aos <= aos + 120): #gpredcit sends different times through the day, varying up to 2 minutes
			return True
	
	return False


def find_fountain_pass(sp):
	global fountain_passes
	for fountain_pass in fountain_passes:
		if (fountain_pass.sat.name == sp.sat.name) and (sp.aos == fountain_pass.start_time):
			return True
	
	return False

def find_sat(name):
	global sats
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

class fake_serial:
	def __init__(self, name):
		self.name = name
		self.last_command = None

	def write(self,command):
		if self.name == "arduino":	
			print self.name," -> ", command, " ",
		self.last_command = command

	def read(self,i):
		if self.name == "arduino":
			if self.last_command == "U":
				return "A"
		else:
			return (chr(6))

	def close(self):
		print "closing ", self.name

	def isOpen(self):
		return True

	def flushInput(self):
		print "",

	def flushOutput(self):
		print "",

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
	global next_pass
	for d in next_pass.details:
		print "times ",my_get_time(), d.time
		if (my_get_time() >= d.time):
			details_now = d
			break

	if next_pass == None:
		print "no data yet"
	else:
		for d in next_pass.details:
			print "%s %s, az: %s, el: %s" %(next_pass.sat.name,get_str_time(d.time), d.az, d.el, )

def print_fountain_passes():
	global fountain_passes
	for fp in fountain_passes:
		print fp.sat.name, fp.start_time, fp.end_time

def filtered_details (p):
	new_details = []
	earliest = detail_end_time = 2000000000
	latest = 0
	for i in range(len(p.details)):
		#laboral only:
		#we don't want the event details that happen in the west part of the sky (> 180 deg azimuth)
		#we don't want event details too close to the horizon (10 deg elevation minimun)
		if (p.details[i].az <= 180) and (p.details[i].el >= 10):
			new_details.append(p.details[i])
			if p.details[i].time < earliest:
				earliest = p.details[i].time

			if i == len(p.details) - 1:
				detail_end_time = p.eos
			else:
				detail_end_time = p.details[i+1].time

			if detail_end_time > latest:
				latest = detail_end_time

			fp = fountain_pass(p.sat, earliest, latest, p.tca_el, new_details)
	return fp

def is_good_pass(p):
	for d in p.details:
		if d.az <= 180 and d.el > 10:
			return True
			break
	return False


def update_fountain_schedule():
	global next_pass, fountain_passes, sat_passes
	fountain_passes = []
	semaphore.acquire()
	#we sort by elevation, to start with the best passes
	sp = sorted(sat_passes, key=lambda sat_pass: sat_pass.tca_el, reverse=True)
	semaphore.release()
	#print "length "+str(len(sat_passes))
	for p in sp:
		if not (find_fountain_pass(p)):
			#laboral only:
			#discard passes that begin AND end on the west side of the sky
			#discard passses lower than 10 deg
			if (is_good_pass(p)): 
				#print "doing the "+p.sat.name    
				if fountain_passes == []:
					fp = filtered_details(p)
					fountain_passes.append(fp)
				else:
					#fp is the last pass to be added to the schedule

					#now    check against all previous passes if there's anything else at the same time
					pass_ok = True
					for cp in fountain_passes:
						#plus 5 seconds before and after - this will be the time to resettle the nozzles
						if ((p.aos >= cp.start_time-5) and (p.aos <= cp.end_time+5)) or ((p.eos>=cp.start_time-5) and (p.eos<=cp.end_time+5)):
							pass_ok = False
							break

					#so ok, no passes at the same time
					if pass_ok == True:
						fp = filtered_details(p)
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
	return 90 - a

def my_get_time():
	#for debug purposes
	return int(time.mktime(time.localtime()))
	#return time.time() - time.timezone

def get_str_time(t=my_get_time()): 
	#print t, time.localtime(t)
	return time.strftime("%H:%M:%S", time.localtime(t))

def start_fountain():
	arduino.write("s00a\n")
	time.sleep(0.1)
	arduino.write("d000\n")
	time.sleep(0.1)
	arduino.write("d010\n")
	time.sleep(0.1)
	arduino.write("d020\n")
	time.sleep(0.1)
	arduino.write("d030\n")
	time.sleep(0.1)
	arduino.write("d040\n")
	time.sleep(0.1)
	arduino.write("d050\n")
	time.sleep(0.1)

def stop_fountain():
	arduino.write("s00d\n")
	time.sleep(0.1)
	arduino.write("d000\n")
	time.sleep(0.1)
	arduino.write("d010\n")
	time.sleep(0.1)
	arduino.write("d020\n")
	time.sleep(0.1)
	arduino.write("d030\n")
	time.sleep(0.1)
	arduino.write("d040\n")
	time.sleep(0.1)
	arduino.write("d050\n")
	time.sleep(0.1)


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
			nnn.append("1")
		else:
			nnn.append("0")
	for i in range(len(nnn)):
		command = "d"+add_zeros_10(i)+nnn[i]+"\n"
		arduino.write(command)
	#print command

def move_nozzle(n,a):
	command = "s"+add_zeros_10(n)+add_zeros_100(a)+"\n"
	arduino.write(command)
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
	#print "text= ", text
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
	#print "ds rec 1"
	ack_or_reset()
	send_sgc_commands(["4C",x+40,y+10,x+44,y+10,0,31]) #line
	#print "ds line 1"
	ack_or_reset()
	send_sgc_commands(["43",x+60,y+10,15,0,31]) #circle
	#print "ds circle"
	ack_or_reset()
	send_sgc_commands(["4C",x+75,y+10,x+80,y+10,0,31]) #line
	#print "ds line 2"
	ack_or_reset()
	send_sgc_commands(["72",x+80,y,x+120,y+20,0,31]) #rectangle
	#print "ds rec 2"
	ack_or_reset()
	


def ack_or_reset():
	global oled

	ack=oled.read(1)
	if (len(ack))==0:
		print "time out exit"
		oled.flushInput()
		oled.flushOutput()
		oled.write("U")
		ack=oled.read(1)
		if (len(ack))==0:
			print "time out exit"
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
	#print "no fill"
	ack_or_reset()
	send_sgc_commands(["72",00,00,159,12,255,255]) #rectangle
	#print "rect title"
	ack_or_reset()
	send_sgc_commands(["70",0]) # fill
	ack_or_reset()
	
	oled_sat_pos = oled_sat_pos + 4
	if (oled_sat_pos == 160):
		oled_sat_pos = 0

	draw_sat(oled_sat_pos,26)
	send_sgc_commands(["70",01]) #no fill
	#print "no fill"
	ack_or_reset()
	sgc_print(7,2,0,248,0,1,1,"ionic satellite fountain")
	#print "title"
	ack_or_reset()
	sgc_print(0,68,2,255,255,1,1,"next pass:")
	#print "next pass"
	ack_or_reset()
	sgc_print(0,83,2,255,255,2,2,satname)
	#print "sat name"
	ack_or_reset()
	if timetext == "now!":
		if now_blink == True:
			sgc_print(0,110,0,255,255,2,2,timetext)
			now_blink = False
		else:
			now_blink = True
	else:
		sgc_print(0,110,0,255,255,2,2,timetext)
	
	#print "time"
	#sgc_print(20,110,0,227,156,2,2,"in 2:10:10")
	ack_or_reset()

#serial ports

def open_serials():
	global arduino, oled

	s1 = None
	s2 = None

	i = 0
	while (s1 == None) and (i<10):
		try:
			s1 = serial.Serial ("/dev/ttyUSB"+str(i),9600, timeout=1)
			s1.open()
		except:
			print "serial port /dev/ttyUSB"+str(i)+" not found ",

		
		i = i + 1


	while (s2 == None) and (i<10):
		try:
			s2 = serial.Serial ("/dev/ttyUSB"+str(i), 9600, timeout=1)
			s2.open()
		except:
			print "serial port /dev/ttyUSB"+str(i)+" not found"
		i = i + 1


	if (s1 == None) or (s2==None):	
		print "one or more devices not found"
		sys.exit()

	s1.flushInput()
	s1.flushOutput()
	s2.flushInput()
	s2.flushOutput()

	#s1.open()
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
			oled.write("U") #set baud rate
			ack_or_reset()
			oled.write("E") #clear screen
			ack_or_reset()
			#print "arduino on USB0"
			#print "oled on USB1"

		elif ord(ack) == 6:
			arduino = s2
			oled = s1
			arduino.write("U")
			ack = arduino.read(1)
			if ack != "A":
				print "arduino not connected "
				sys.exit()
			oled.write("U") #set baud rate
			ack_or_reset()
			oled.write("E") #clear screen
			ack_or_reset()
			#print "arduino on USB1"
			#print "oled on USB0"
		else:
			print "device 1 not responding"

	else:
		print "something is wrong :-O "
		print "try again in a few seconds "
		print "if still not working reconnect the cables"
		sys.exit()

	print "arduino on "+arduino.port
	print "oled on "+oled.port

#data and initialization

# satellite and frequency list
sat_data = [
	#{'name':'AO-7', 'freq':145977500, 'mode':'cw'},
	{'name':"HO-68", 'freq':437275000, 'mode':'cw'},
	{'name':'AO-7', 'freq':435106000, 'mode':'cw'},
	{'name':'AO-27', 'freq':436795000, 'mode':'fm'},
	{'name':'CO-55', 'freq':436837500, 'mode':'cw'},
	{'name':'CO-58', 'freq':437425000, 'mode':'cw'},
	{'name':'NOAA 15', 'freq':137620000, 'mode':'fm'},
	{'name':'NOAA 17', 'freq':137500000, 'mode':'fm'},
	{'name':'NOAA 18', 'freq':137912500, 'mode':'fm'},
	{'name':'NOAA 19', 'freq':137100000, 'mode':'fm'},
	{'name':'CO-57', 'freq':436847500, 'mode':'cw'},
	{'name':'COMPASS-1', 'freq':435790000, 'mode':'cw'},
	{'name':'VO-52', 'freq':145936000, 'mode':'cw'},
	{'name':'SEEDS II', 'freq':437485000, 'mode':'cw'},
	{'name':'DELFI-C3', 'freq':145870000, 'mode':'cw'},
	{'name':'SO-67', 'freq':435300000, 'mode':'fm'},#
	{'name':'UWE-2', 'freq':437385000, 'mode':'fm'},#
	{'name':'SO-50', 'freq':436795000, 'mode':'fm'},
	{'name':'SWISSCUBE', 'freq':437505000, 'mode':'cw'},#
	{'name':'ITUPSAT 1', 'freq':437325000, 'mode':'cw'},#
	{'name':'BEESAT', 'freq':436000000, 'mode':'cw'},#
	{'name':'FO-29', 'freq':435795000, 'mode':'cw'},
	{'name':'ISS', 'freq':145825000, 'mode':'cw'},
	{'name':'PRISM', 'freq':437250000, 'mode':'cw'},
	{'name':'AAU CUBESAT', 'freq':437900000, 'mode':'cw'},
	{'name':'STARS', 'freq':437305000, 'mode':'cw'},
	{'name':'KKS-1', 'freq':437385000, 'mode':'cw'},
	{'name':'CUTE-1.7+APD II', 'freq':437275000, 'mode':'cw'},
]

#sat_data[0]['name'] = "HOPE-1 (HO-68)"+chr(13)+chr(10) #it's coming from gpredict this way

IS_JUST_A_TEST = False

pins = [0,0,0,0,0,0]



arduino = oled = None


if IS_JUST_A_TEST is False: 	
	open_serials()
else:
	arduino = fake_serial("arduino")
	oled = fake_serial("oled")


#laboral is inclined 8deg to true north
#first nozzle at 15deg from building alignment, ie 23deg
#the others 30deg spaced
nozzles_azimuth = [23, 53,83, 113, 143, 173] 


step = 10




try :

	time.sleep(12)

	start_fountain()
	# 0 s, n 1, angle 12
	# 39 s, n 1, angle 16
	# 40 s, n 1, angle 22

	nozzle_solo(0)
	move_nozzle(0,90-12)
	time.sleep(step)
	move_nozzle(0,90-16)
	time.sleep(step)
	move_nozzle(0,90-22)
	time.sleep(step)
	move_nozzle(0,90-30)
	time.sleep(step)
	move_nozzle(0,90-40)
	time.sleep(step)

	nozzle_solo(1)
	move_nozzle(1,90-54)
	time.sleep(step)

	nozzle_solo(2)
	move_nozzle(2,90-63)
	time.sleep(step)

	nozzle_solo(3)
	move_nozzle(3,90-10)
	time.sleep(step)
	move_nozzle(3,90-16)
	time.sleep(step)
	move_nozzle(3,90-22)
	time.sleep(step)
	move_nozzle(3,90-30)
	time.sleep(step)
	move_nozzle(3,90-40)
	time.sleep(step)

	nozzle_solo(4)
	move_nozzle(4,90-56)
	time.sleep(step)

	nozzle_solo(5)
	move_nozzle(5,90-42)
	time.sleep(step)
	move_nozzle(5,90-31)
	time.sleep(step)
	move_nozzle(5,90-23)
	time.sleep(step)
	move_nozzle(5,90-17)
	time.sleep(step)

	stop_fountain()
	if arduino != None:
		if arduino.isOpen(): 
			arduino.close()
	if oled != None:
		if oled.isOpen(): 
			oled.close()

	print "Done"


except KeyboardInterrupt :
	stop_fountain()
	if arduino != None:
		if arduino.isOpen(): 
			arduino.close()
	if oled != None:
		if oled.isOpen(): 
			oled.close()

	print "Done"


