
""" 
pass data: satname, aos time, aos azimuth, tca time, tca elevation, tca azimuth, eos time, eos azimuth
pass detail data: time, azimuth, elevation


"""


from simpleOSC import *
import time, sys, select

global current_pass

current_pass = -1

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


initOSCServer('127.0.0.1', 7770)

sats = []
sat_passes = []
fountain_passes = []



# define a message-handler function for the server to call.
def pass_handler(addr, tags, data, source):
    global current_pass
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
    current_pass = p

    
def detail_handler(addr, tags, data, source):
    global current_pass
    d = pass_detail(data[0], data[1], data[2])
    if (current_pass == -1):
        print "bug - pass detail before pass"
    else:
        current_pass.add_detail(d)
   
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

def update_fountain_schedule():
    sp = sorted(sat_passes, key=lambda sat_pass: sat_pass.tca_el, reverse=True)
    for p in sp:
        if fountain_passes == []:
            fp = fountain_pass(p.sat, p.aos, p.eos, p.tca_el, p.details)
            fountain_passes.append(fp)
        else:
            #fp is the last pass to be added to the schedule
            
            #now check against all previous passes if there's anything else at the same time
            pass_ok = True
            for cp in fountain_passes:
                if ((p.aos >= cp.start_time) and (p.aos <= cp.end_time)) or ((p.eos>=cp.start_time) and (p.eos<=cp.end_time)):
                    pass_ok = False
                    break
            if pass_ok == True:
                fp = fountain_pass(p.sat, p.aos, p.eos, p.tca_el, p.details)
                fountain_passes.append(fp)
            else:
                continue
             
    fountain_passes.sort(key=lambda fountain_pass: fountain_pass.start_time)
    print_schedule(fountain_passes)


setOSCHandler("/gpredict/sats/all", sat_handler) # adding our function
setOSCHandler("/gpredict/sats/next", sat_handler) # adding our function
setOSCHandler("/gpredict/sats", sat_handler) # adding our function

setOSCHandler("/gpredict/pass", pass_handler) # adding our function
setOSCHandler("/gpredict/pass/detail", detail_handler) # adding our function


# just checking which handlers we have added. not really needed
reportOSCHandlers()



try :
    while 1 :
        time.sleep(1)
        if heard_enter():
            #print_passes(sat_passes)
            update_fountain_schedule()

except KeyboardInterrupt :
    print "\nClosing OSCServer."
    print "Waiting for Server-thread to finish"
    closeOSC()
    print "Done"
        


