#!/usr/bin/python3

# program to log battery data from Eco-worthy LiFePo4 batteries
# probably works with other batteries that use similar BMS
# BMS maker: https://jiabaida-bms.com/pages/download-files
# Look for: JDB RS485-RS232-UART-Bluetooth-Communication Protocol
# mike805@pobox.com 2025-01-02

# bluepy seems to have a problem where one incoming response gets stuck in the pipe
# the response only comes in when another request is sent to the battery
# this program tries to avoid the problem

from bluepy.btle import Peripheral, DefaultDelegate
import datetime
import time
import sys
import os

service_uuid = 0xff00
characteristic_uuid = 0xff02

# Define a delegate class to handle notifications
class MyDelegate(DefaultDelegate):

    def __init__(self,device_address,logfile,get_cell_voltages):
        self.params1 = None
        self.params1len = None
        self.params2 = None
        self.params2len = None
        self.voltage = None
        self.current = None
        self.ahrem = None
        self.ahmax = None
        self.watts = None
        self.last_soc = None
        self.soc = None
        self.temp = None
        self.device_address = device_address
        self.logfile = logfile
        self.now_dt = None
        self.now_date = None
        self.now_time = None
        self.switches = None
        self.pending_params2 = False
        self.n_cells = None
        self.cell_voltages = [ ]
        self.check_done = False
        self.get_cell_voltages = get_cell_voltages
        DefaultDelegate.__init__(self)

    def handleNotification(self, cHandle, data):
        print("Packet", data.hex())
        
        if (data[0:2] == b'\xdd\x04'):
            self.params2 = data
            self.params2len = int.from_bytes(data[2:4],'big')
            self.pending_params2 = True
            self.testDecodeParams2()
        elif (data[0:2] == b'\xdd\x03'):
            self.params1 = data
            self.params1len = int.from_bytes(data[2:4],'big')
            self.now_dt = datetime.datetime.fromtimestamp(time.time())
            self.now_date = datetime.datetime.strftime(self.now_dt,"%Y-%m-%d")
            self.now_time = datetime.datetime.strftime(self.now_dt,"%H:%M:%S")
            self.testDecodeParams1()
        elif self.pending_params2 == True:
            self.params2 += data
            self.testDecodeParams2()
        else:
            self.params1 += data
            self.testDecodeParams1()

    def testDecodeParams1(self):
        #print("len1",self.params1len,"got",len(self.params1))
        if (len(self.params1) >= (self.params1len + 7)):
            if (len(self.params1) != (self.params1len + 7)):
                print("Received:", self.params1.hex())
                print("Length invalid, expected ",self.params1len,", got",self.params1.length)
                self.clearVars()
            elif (self.params1[len(self.params1) - 1] != 0x77):
                print("Received:", self.params1.hex())
                print("End byte:",self.params1[len(self.params1) - 1].hex())
                print("End byte invalid")
                self.clearVars()
            else:
                print("Received:", self.params1.hex())
                self.decodeParams1()
                if self.get_cell_voltages == False:
                    self.printDataLong()
                    if self.logfile != None:
                        self.printDataCsv()
                    self.clearVars()
                    self.check_done = True

    def testDecodeParams2(self):
        #print("len2",self.params2len,"got",len(self.params2))
        if (len(self.params2) >= (self.params2len + 7)):
            if (len(self.params2) != (self.params2len + 7)):
                print("Received:", self.params2.hex())
                print("Length invalid, expected ",self.params2len,", got",self.params2.length)
                self.pending_params2 = False
            elif (self.params2[len(self.params2) - 1] != 0x77):
                print("Received:", self.params2.hex())
                print("End byte:",self.params2[len(self.params2) - 1].hex())
                print("End byte invalid")
                self.pending_params2 = False
            else:
                print("Received2:", self.params2.hex())
                self.pending_params2 = False
                self.decodeParams2()
                self.printDataLong()
                if self.logfile != None:
                    self.printDataCsv()
                self.clearVars()
                self.check_done = True

    def decodeParams1(self):
        self.voltage = int.from_bytes(self.params1[4:6],'big')
        self.current = int.from_bytes(self.params1[6:8],'big')
        if (self.current > 0x7fff):
            self.current = self.current - 0x10000
        self.ahrem = int.from_bytes(self.params1[8:10],'big')
        self.ahmax = int.from_bytes(self.params1[10:12],'big')
        self.watts = (self.voltage * self.current) / 10000.0
        if self.ahmax == 0:
            self.soc = 0.0
        else:
            self.soc = 100.0 * (self.ahrem / self.ahmax)
        self.temp = (int.from_bytes(self.params1[27:29],'big') - 2731) * 0.1
        switches = int.from_bytes(self.params1[24:25],'big')
        if (switches & 1) == 1:
            self.switches = 'C+'
        else:
            self.switches = 'C-'
        if (switches & 2) == 2:
            self.switches += 'D+'
        else:
            self.switches += 'D-'

    def decodeParams2(self):
        self.n_cells = int(int.from_bytes(self.params2[3:4],'big') / 2)
        i = 4
        n = 0
        while n < self.n_cells:
            self.cell_voltages.append(int.from_bytes(self.params2[i:i+2],'big'))
            i += 2
            n += 1 

    def printDataLong(self):
        print("  Time: " + self.now_date + ' ' + self.now_time)
        print("Bat ID: " + self.device_address)
        print(" Volts: {:>6.2f}".format(self.voltage / 100))
        print("  Amps: {:>6.2f}".format(self.current / 100))
        print("SOC Ah: {:>6.2f}".format(self.ahrem / 100))
        print("Max Ah: {:>6.2f}".format(self.ahmax / 100))
        print(" Watts: {:>6.2f}".format(self.watts))
        print(" SOC %: {:>6.2f}".format(self.soc))
        print("  Temp: {:>6.2f}".format(self.temp))
        print("Switch:   " + self.switches)
        if self.n_cells != None:
            i = 0
            while i < self.n_cells:
                print("Cell{:>2d}: {:>6.3f}".format(i,self.cell_voltages[i] / 1000))
                i += 1

    def printDataCsv(self):
        file_existed = os.path.exists(self.logfile)
        fp = open(self.logfile,'a')
        if file_existed == False:
            header = "date,time,macaddr,volts,amps,soc_ah,max_ah,watts,soc_pct,temp,switch"
            if self.n_cells != None:
                i = 0
                while i < self.n_cells:
                    header += ",cell{:>02d}".format(i)
                    i += 1
            fp.write(header + "\n")
        lineout = self.now_date + ',' + self.now_time + ',' + \
                  device_address + ',' + \
                  "{:.2f}".format(self.voltage / 100) + ',' + \
                  "{:.2f}".format(self.current / 100) +  ',' + \
                  "{:.2f}".format(self.ahrem / 100) + ',' + \
                  "{:.2f}".format(self.ahmax / 100) + ','  + \
                  "{:.2f}".format(self.watts) + ',' + \
                  "{:.2f}".format(self.soc) + ',' + \
                  "{:.2f}".format(self.temp) + ',' + \
                  self.switches
        if self.n_cells != None:
            i = 0
            while i < self.n_cells:
                lineout += ",{:>.3f}".format(self.cell_voltages[i] / 1000)
                i += 1
        fp.write(lineout + "\n")
        fp.close()

    def clearVars(self):
        self.params1 = None
        self.params1len = None
        self.params2 = None
        self.params2len = None
        self.voltage = None
        self.current = None
        self.power = None
        self.ahrem = None
        self.ahmax = None
        self.watts = None
        self.last_soc = self.soc
        self.soc = None
        self.temp = None
        self.switches = None
        self.n_cells = None
        self.cell_voltages = [ ]
        self.now_dt = None
        self.now_date = None
        self.now_time = None

device_address = None
logfile = None
interval = None
get_cell_voltages = False
exit_if_above = None
exit_if_below = None

cmdline = sys.argv[1:]
n = 0
l = len(cmdline)
while n < l:
    c = cmdline[n]
    if c == '-m':
        n += 1
        if n < l:
            device_address = cmdline[n]
    elif c == '-l':
        n += 1
        if n < l:
            logfile = cmdline[n]
    elif c == '-i':
        n += 1
        if n < l:
            interval = int(cmdline[n])
    elif c == '-a':
        n += 1
        if n < l:
            exit_if_above = float(cmdline[n])
    elif c == '-b':
        n += 1
        if n < l:
            exit_if_below = float(cmdline[n])
    elif c == '-v':
        get_cell_voltages = True
    n += 1

if device_address == None:
    print("Usage: python ewbatlog.py -m mac-address [-i interval] [-l logfile] [-a pct] [-b pct] [-v]")
    print("Mac address format: a5:c2:37:01:2f:ed")
    print("Interval is in seconds, logfile is for csv output, -v to get cell voltages")
    print("-a pct exits with code 2 if above SOC percentage")
    print("-b pct exits with code 3 if below SOC percentage")
    sys.exit(1) 

exit_after_once = False
exit_code = 0
if interval == None:
    interval = 1
    exit_after_once = True

#print("device_address",device_address)
#print("logfile",logfile)
#print("interval",interval)
#print("exit_after_once",exit_after_once)
#print("get_cell_voltages",get_cell_voltages)

try:
    # Connect to the device
    device = Peripheral(device_address)
except Exception as e:
    print("Failed to connect to battery:",e)
    sys.exit(1)

try:
    # Set the notification delegate
    delegate = MyDelegate(device_address,logfile,get_cell_voltages)
    device.withDelegate(delegate)

    # Get the service
    service = device.getServiceByUUID(service_uuid)

    # Get the characteristic
    characteristic = service.getCharacteristics(characteristic_uuid)[0]

    # The "withResponse" option to the wr command determines whether a response is required or not. Set it to False for a write command (opcode 0x52) and set to True for a write request (opcode 0x12) with a response. The default value is False.

    # Wait for notifications
    lasttime = time.time() - interval
    send_voltage_query = False
    while True:
        if device.waitForNotifications(1.0):
            # returns True when notification received, False when timeout
            # handleNotification() will be called when a notification is received
            continue
        if ((exit_after_once == True) and (delegate.check_done == True)):
            exit_code = 0
            break
        if ((exit_if_above != None) and (delegate.last_soc != None) and
            (delegate.last_soc > exit_if_above)):
            exit_code = 2
            break
        elif ((exit_if_below != None) and (delegate.last_soc != None) and
            (delegate.last_soc < exit_if_below)):
            exit_code = 3
            break

        nowtime = time.time()
        if send_voltage_query == True:
            send_voltage_query = False
            characteristic.write(b'\xdd\xa5\x04\x00\xff\xfc\x77',withResponse = False)
            print("Sent cell voltage query")
        elif (nowtime >= (lasttime + interval)):
            lasttime += interval
            characteristic.write(b'\xdd\xa5\x03\x00\xff\xfd\x77',withResponse = False)
            print("Sent volts/amps/state of charge query")
            send_voltage_query = get_cell_voltages

finally:
    # Disconnect from the device
    device.disconnect()
    sys.exit(exit_code) 

# EOF
