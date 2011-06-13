
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
// d051 - turn on nozzle 5 (on pin 13)
// s03080 - turn servo 3 (on pin 10) to 80 degress


"""


from simpleOSC import *
import time, sys, select, threading, serial

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
    def __init__(self, time, az, el):
        self.time = time
        self.az=az
        self.el=el



IS_JUST_A_TEST = True

index_pass = -1
current_pass = None
next_pass = None

semaphore = threading.BoundedSemaphore()

initOSCServer('127.0.0.1', 7770)

sp = serial.Serial("/dev/ttyUSB0", 57600, timeout=0.02)

sats = []
sat_passes = []
fountain_passes = []

#laboral is inclined 8deg to true north
#first nozzle at 15deg from building alignment, ie 23deg
#the others 30deg spaced
nozzles_azimuth = [23, 53,83, 113, 143, 173] 

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
    d = pass_detail(data[0], data[1], data[2])
    if (index_pass == -1):
        print "no pass? bug"
    else:
        index_pass.add_detail(d)
   
# define a message-handler function for the server to call.
def sat_handler(addr, tags, data, source):
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
            sp.write(str)

def move_nozzle(n,a):
    str = "s"+add_zeros_10(n)+add_zeros_100(a)+"\n"
    if IS_JUST_A_TEST:
        print "angle %s command %s" % ( a)
    else:
        sp.write(str)

setOSCHandler("/gpredict/sats/all", sat_handler) # adding our function
setOSCHandler("/gpredict/sats/next", sat_handler) # adding our function
setOSCHandler("/gpredict/sats", sat_handler) # adding our function
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
        if (next_pass != None):
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
                print ""

            else:
                #no activity - go ahead and update the schedule
                print "else"
                update_fountain_schedule()

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
        


