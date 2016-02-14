#!/usr/bin/python

import Adafruit_CharLCD as LCD
from subprocess import *
from time import sleep, strftime
from datetime import datetime
from array import array
import RPi.GPIO as GPIO
import threading
import Queue
import urllib2
mode = 0
sshran = 0
vlan = 0
vlandone = 0
port = 0
portdone = 0
quit = 0
cursorval = 0
cursorpos = 0
color = [1.0,1.0,1.0]
staticip = [0,0,0,'.',0,0,0,'.',0,0,0,'.',0,0,0]
staticon = 0 #static ip enabled indicator
#lcd = LCD.Adafruit_CharLCDPlate()
#lcd.set_color(0.0,0.1,1.0)
#GPIO.setmode(GPIO.BCM)
#GPIO.setup(12, GPIO.IN, pull_up_down=GPIO.PUD_UP)
#GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)
class connectManager(threading.Thread):
    def run(self):
        global isup
        global mode
        global port
        global portdone
        global vlan
        global vlandone
        while quit==0:
            if (int(run_cmd(cmd2))==0):
                if (isup == 1): #new disconnect
                    run_cmd('dhclient -r eth0')
                    vlan = 0
                    vlandone = 0
                    port = 0
                    portdone = 0
                    run_cmd('pkill tcpdump')
                    isup = 0
            else: #Current status connected
                if (isup == 0):
                    if len(run_cmd(cmd).rstrip())==0:
                        display.queue.put([datetime.now().strftime('%b %d  %H:%M:%S\n') + 'Renewing DHCP...',[1,0,1]])
                        mode=0
                        print "VLANSTARTCONNECT"
                        vlanFinder(vlancmd).start()
                        portFinder(portcmd).start()
                        vlanFinder(vlancdpcmd).start()
                        portFinder(portcdpcmd).start()
                        print "CONNECTDONE"
                        isup = 2
                        run_cmd('dhclient eth0')
                    isup = 1
            sleep(1)
class screenWriter(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.lcd = LCD.Adafruit_CharLCDPlate()
        self.lcd.set_color(color[0],color[1],color[2])
        self.lcd.message("Starting Up")
        self.lcd.create_char(1, [2, 3, 2, 2, 14, 30, 12, 0])
        self.lcd.create_char(2, [0, 1, 3, 22, 28, 8, 0, 0])
        self.queue = Queue.Queue()
    def run(self):
        global color
        global mode
        while quit==0:
            messagetoprint = self.queue.get()
            if messagetoprint[1] == "***": #flag for directwrite
                #sleep(0.05)
                self.lcd.write8(ord(str(messagetoprint[0])),char_mode = True)
                #sleep(0.05)
                continue
            if messagetoprint[1] == "*BLINK*":
                self.lcd.blink(messagetoprint[0])
                continue
            if messagetoprint[1] == "*SETCSR*":
                self.lcd.set_cursor(messagetoprint[0][0], messagetoprint[0][1])
                continue
            if messagetoprint[1] != color:
                self.lcd.set_color(messagetoprint[1][0],messagetoprint[1][1],messagetoprint[1][2])
                color[0] = messagetoprint[1][0]
                color[1] = messagetoprint[1][1]
                color[2] = messagetoprint[1][2]
            self.lcd.clear() #each message should fill the entire screen
            self.lcd.message(messagetoprint[0])
            if mode > 100 and mode != 131:
                self.lcd.blink(True)
            else:
                self.lcd.blink(False)
def writeDisplay(message, newcolor = color):
    display.queue.put([message,newcolor])
class buttonHandler(threading.Thread):
    def run(self):
        global mode
        global display
        global shutdown
        global cursorval
        global cursorpos
        newbutton = 0
        newcursor = 0
        while quit == 0:
            if display.lcd.is_pressed(LCD.UP):
                if mode > 100:
                    newcursor = 1
                    cursorval = cursorval + 1
                    if cursorval>9:
                        cursorval = 0
                else:
                    newbutton = 1
                    mode = mode - 1
                    if mode<0:
                        mode = 4
            if display.lcd.is_pressed(LCD.DOWN):
                if mode > 100:
                    newcursor = 1
                    cursorval = cursorval - 1
                    if cursorval<0:
                        cursorval = 9
                else:
                    newbutton = 1
                    mode = mode + 1
                    if mode>4:
                        mode = 0
            if display.lcd.is_pressed(LCD.RIGHT):
                if mode == 0:
                    mode = 101
                #elif mode == 3:
                #   mode = 131
                #elif mode == 131:
                #   mode = 3
                if mode == 101 or mode == 102 or mode == 103 or mode == 104:
                    newcursor = 2
                    cursorpos = cursorpos+1;
                    if mode == 104:
                        pass #don't jump decimals on the confirm screen
                    elif cursorpos == 3 or cursorpos == 7 or cursorpos == 11:
                        cursorpos = cursorpos + 1;
                    if cursorpos >= 15:
                        cursorpos = 0
                        if mode == 101:
                            mode = 102
                        elif mode == 102:
                            mode = 103
                        elif mode == 103:
                            mode = 104
                        elif mode == 104:
                            mode = 105
            if display.lcd.is_pressed(LCD.LEFT):
                #if mode == 3:
                #   mode = 131
                #elif mode == 131:
                #   mode = 3
                if mode == 101 or mode == 102 or mode == 103 or mode == 104:
                    newcursor = 2
                    cursorpos = cursorpos - 1;
                    if mode == 104:
                        pass #don't jump decimals on the confirm screen
                    elif cursorpos == 3 or cursorpos == 7 or cursorpos == 11:
                        cursorpos = cursorpos - 1;
                    if cursorpos < 0:
                        cursorpos = 0
                        if mode == 104:
                            mode = 103
                        elif mode == 103:
                            mode = 102
                        elif mode == 102:
                            mode = 101
                        elif mode == 101:
                            mode = 0 #should be cancel screen
            if display.lcd.is_pressed(LCD.SELECT):
                shutdown()
            if newbutton == 1:
                display.queue.put(['Please Wait...\nCleaning Up',[1.0,0.5,0.0]])
                run_cmd("pkill ping")
                newbutton = 0
                sleep(0.5) #500ms debounce
            if newcursor > 0:
                #display.lcd.blink(False)
                #display.lcd.set_cursor(cursorpos,1)
                #display.lcd.blink(True)
                writeDisplay(False,"*BLINK*")
                writeDisplay([cursorpos,1],"*SETCSR*")
                writeDisplay(True,"*BLINK*")
                sleep(0.2) #500ms debounce
                newcursor = 0
            else:
                sleep(0.01) #poll button every 10ms
class remoteSSH(threading.Thread):
    def run(self):
        run_cmd("sshpass -p 00-23-7D-BA-1B-59 ssh raspberrypi@lucario.info -p 448 -f -N -R 2200:localhost:22 & echo $!").rstrip()
class vlanFinder(threading.Thread):
    def __init__(self, cmd):
        threading.Thread.__init__(self)
        self.cmd = cmd
    def run(self):
        global vlan
        global vlandone
        vlan = "Searching..."
        tempvlan = run_cmd(self.cmd)
        if (len(tempvlan)>0):
            vlan = tempvlan
            vlandone = 1
        if(len(tempvlan) == 0 and vlandone == 0):
            vlan = "None found"
        elif(vlan == "Searching..."):
            vlan = "None found"
class portFinder(threading.Thread):
    def __init__(self, cmd):
        threading.Thread.__init__(self)
        self.cmd = cmd
    def run(self):
        global port
        global portdone
        port = " Searching..."
        tempport = run_cmd(self.cmd)
        if(len(tempport)>0):
            port = tempport
            portdone = 1
        if(len(port) == 0 and portdone == 0):
            port = " None found"
        elif(port == " Searching..."):
            port = " None found"
def dhcpRenew(channel):
    run_cmd('dhclient -r eth0')
    run_cmd('dhclient eth0')
#def buttonHandler(channel):
#    global mode
#    lcd.clear()
#    lcd.message('Please Wait...\nCleaning Up')
#    mode = mode + 1
#    if (mode>3):
#        mode = 0
#    run_cmd("pkill ping")
def shutdown():
    global mode
    mode = 99 #stop displaying other messages
    writeDisplay('Shutting Down...\nUnplug after 15',[1.0,0,0])
    sleep(0.1)
    run_cmd("halt")

#GPIO.add_event_detect(12, GPIO.FALLING, callback=buttonHandler, bouncetime=300)
#GPIO.add_event_detect(16, GPIO.FALLING, callback=shutdown, bouncetime=300)

cmd = "ifconfig eth0 | grep -oP 'inet addr:\K.*' | awk '{print $1}'"
cmd2 = "cat /sys/class/net/eth0/carrier"
googlecmd = "ping -c 1 8.8.8.8 | grep -oP 'time=\K.*'"
routercmd = "route -n | grep UG | awk '{print $2}'"
dnscmd = "host vcu.edu | grep -oP 'has address \K.*'"
maccmd = "ifconfig | grep -oP 'HWaddr \K.*' | sed 's/-\|:\|\s//g'"
vlancmd = "timeout --foreground 35 tcpdump -nn -v -i eth0 -s 1500 -c 1 '(ether[12:2]=0x88cc)' | grep '(VID):' | awk '{print $4}'"
vlancdpcmd = "timeout --foreground 35 tcpdump -nn -v -i eth0 -s 1500 -c 1 '(ether[20:2]=0x2000)' | grep 'Native VLAN ID' | awk '{print $8}'"
portcmd = "timeout --foreground 35 tcpdump -nn -v -i eth0 -s 1500 -c 1 '(ether[12:2]=0x88cc)' | grep 'Port Description TLV' | awk '{print $7}'"
portcdpcmd = "timeout --foreground 35 tcpdump -nn -v -i eth0 -s 1500 -c 1 '(ether[20:2]=0x2000)' | grep 'Port-ID' | awk '{print $6}'"
speedcmd = "ethtool eth0 | grep -oP 'Speed:\K.*' | awk '{print $1}'"
duplexcmd = "ethtool eth0 | grep -oP 'Duplex:\K.*' | awk '{print $1}'"

#lcd.begin(16, 1)

def run_cmd(cmd):
    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.communicate()[0]
    return output
isup = int(run_cmd(cmd2))
display = screenWriter()
display.start()
buttonthread = buttonHandler()
buttonthread.start()
connectmanager = connectManager()
connectmanager.start()
print "VLANSTARTINIT"
vlanFinder(vlancmd).start()
portFinder(portcmd).start()
vlanFinder(vlancdpcmd).start()
portFinder(portcdpcmd).start()
print "INITDONE"
while 1:
    try:
        if (mode == 0):
            ipaddr = run_cmd(cmd).rstrip()
            if (int(isup)==1):
                if (staticon):
                    writeDisplay(datetime.now().strftime('%b %d  %H:%M:%S\n')+'IP '+ipaddr,[1,1,1])
                else:
                    writeDisplay(datetime.now().strftime('%b %d  %H:%M:%S\n')+'IP '+ipaddr,[0,0.1,1])
            elif (int(isup)==2):
                writeDisplay(datetime.now().strftime('%b %d  %H:%M:%S\n')+'Renewing DHCP',[1,0,1])
            else:
                writeDisplay(datetime.now().strftime('%b %d  %H:%M:%S\n')+'Ethernet Down',[1,0.5,0])
            for x in range(19):
                if (mode == 0):
                    sleep(0.1)
        elif (mode == 101):
            writeDisplay("Set Static IP:\n")
            cursorpos = 0
            for char in staticip:
                writeDisplay(char,"***")
            cursorpos = 0
            oldcursorpos = 0
            cursorval = staticip[cursorpos]
            oldcursorval = 0
            sleep(0.2)
            while mode == 101:
                writeDisplay([cursorpos,1],"*SETCSR*")
                writeDisplay(cursorval,"***")
                writeDisplay([cursorpos,1],"*SETCSR*")
                for x in range(20):
                    if (mode == 101 and oldcursorpos == cursorpos and oldcursorval == cursorval):
                        sleep(0.1)
                if oldcursorval != cursorval: #stop values from going over 255
                    cursoroctet = [staticip[cursorpos//4*4],staticip[cursorpos//4*4+1],staticip[cursorpos//4*4+2]]
                    cursoroctet[cursorpos%4] = cursorval
                    if int(str(cursoroctet[0])+str(cursoroctet[1])+str(cursoroctet[2]))>255:
                        cursorval = oldcursorval
                if oldcursorpos != cursorpos:
                    staticip[oldcursorpos] = cursorval
                    cursorval = staticip[cursorpos]
                oldcursorpos = cursorpos
                oldcursorval = cursorval
        elif (mode == 102):
            writeDisplay("Netmask:\n")
            if staticon == 0:
                if staticip[0] == 0 and staticip[1] == 1 and staticip[2] == 0: #simple default netmasks
                    netmask = [2,5,5,'.',0,0,0,'.',0,0,0,'.',0,0,0]
                else:
                    netmask = [2,5,5,'.',2,5,5,'.',2,5,5,'.',0,0,0]
            cursorpos = 0
            for char in netmask:
                writeDisplay(char,"***")
            cursorpos = 0
            oldcursorpos = 0
            cursorval = netmask[cursorpos]
            oldcursorval = 0
            sleep(0.2)
            while mode == 102:
                writeDisplay([cursorpos,1],"*SETCSR*")
                writeDisplay(cursorval,"***")
                writeDisplay([cursorpos,1],"*SETCSR*")
                for x in range(20):
                    if (mode == 102 and oldcursorpos == cursorpos and oldcursorval == cursorval):
                        sleep(0.1)
                if oldcursorval != cursorval: #stop values from going over 255
                    cursoroctet = [netmask[cursorpos//4*4],netmask[cursorpos//4*4+1],netmask[cursorpos//4*4+2]]
                    cursoroctet[cursorpos%4] = cursorval
                    if int(str(cursoroctet[0])+str(cursoroctet[1])+str(cursoroctet[2]))>255:
                        netmask[cursorpos//4*4],netmask[cursorpos//4*4+1],netmask[cursorpos//4*4+2] = 2,5,5
                        cursorval = netmask[cursorpos]
                        writeDisplay([0,1],"*SETCSR*")
                        for char in netmask:
                            writeDisplay(char,"***")
                        writeDisplay([cursorpos,1],"*SETCSR*")
                if oldcursorpos != cursorpos:
                    netmask[oldcursorpos] = cursorval
                    cursorval = netmask[cursorpos]
                oldcursorpos = cursorpos
                oldcursorval = cursorval
        elif (mode == 103):
            sipoc = [int(str(staticip[0]) + str(staticip[1]) + str(staticip[2])), int(str(staticip[4]) + str(staticip[5]) + str(staticip[6])), int(str(staticip[8]) + str(staticip[9]) + str(staticip[10])), int(str(staticip[12]) + str(staticip[13]) + str(staticip[14]))]
            nmoc = [int(str(netmask[0]) + str(netmask[1]) + str(netmask[2])), int(str(netmask[4]) + str(netmask[5]) + str(netmask[6])), int(str(netmask[8]) + str(netmask[9]) + str(netmask[10])), int(str(netmask[12]) + str(netmask[13]) + str(netmask[14]))]
            gatewayipoc = [sipoc[0]//(256-nmoc[0])*(256-nmoc[0]),sipoc[1]//(256-nmoc[1])*(256-nmoc[1]),sipoc[2]//(256-nmoc[2])*(256-nmoc[2]),(sipoc[3]//(256-nmoc[3])*(256-nmoc[3]))+1]
            gatewayip = list()
            for octet in gatewayipoc:
                gatewayip.append(int('{0:03d}'.format(octet)[0]))
                gatewayip.append(int('{0:03d}'.format(octet)[1]))
                gatewayip.append(int('{0:03d}'.format(octet)[2]))
                gatewayip.append('.')
            del gatewayip[-1] # remove last period
            writeDisplay("Gateway IP:\n")
            cursorpos = 0
            for char in gatewayip:
                writeDisplay(char,"***")
            cursorpos = 0
            oldcursorpos = 0
            cursorval = gatewayip[cursorpos]
            oldcursorval = 0
            sleep(0.2)
            while mode == 103:
                writeDisplay([cursorpos,1],"*SETCSR*")
                writeDisplay(cursorval,"***")
                writeDisplay([cursorpos,1],"*SETCSR*")
                for x in range(20):
                    if (mode == 103 and oldcursorpos == cursorpos and oldcursorval == cursorval):
                        sleep(0.1)
                if oldcursorval != cursorval: #stop values from going over 255
                    cursoroctet = [gatewayip[cursorpos//4*4],gatewayip[cursorpos//4*4+1],gatewayip[cursorpos//4*4+2]]
                    cursoroctet[cursorpos%4] = cursorval
                    if int(str(cursoroctet[0])+str(cursoroctet[1])+str(cursoroctet[2]))>255:
                        cursorval = oldcursorval
                if oldcursorpos != cursorpos:
                    gatewayip[oldcursorpos] = cursorval
                    cursorval = gatewayip[cursorpos]
                oldcursorpos = cursorpos
                oldcursorval = cursorval
        elif (mode == 104):
            cursorpos = 0
            oldcursorpos = 0
            writeDisplay('Are you sure?\nX No       Yes \x02',[1,0.5,0])
            writeDisplay([cursorpos,1],"*SETCSR*")
            while mode == 104:
                sleep(0.1)
        elif (mode == 105):
            writeDisplay('Please Wait...\nChanging IP',[1,0,1])
            stringstaticip = ""
            stringnetmask = ""
            stringgateway = ""
            for x in range(4): # per octet
                tempstringip = ""
                tempstringnm = ""
                tempstringgw = ""
                for y in range(3): # per char
                    tempstringip = tempstringip + str(staticip[x*4+y])
                    tempstringnm = tempstringnm + str(netmask[x*4+y])
                    tempstringgw = tempstringgw + str(gatewayip[x*4+y])
                stringstaticip = stringstaticip + str(int(tempstringip)) + '.' # remove leading zeroes
                stringnetmask = stringnetmask + str(int(tempstringnm)) + '.' # remove leading zeroes
                stringgateway = stringgateway + str(int(tempstringgw)) + '.' # remove leading zeroes
            staticcmd = "ifconfig eth0 " + stringstaticip[:-1] + " netmask " + stringnetmask[:-1] #[:-1] lol
            routecmd = "route add default gw " + stringgateway[:-1] + " eth0"
            run_cmd(staticcmd)
            run_cmd(routecmd)
            staticon = 1
            mode = 0
            print "DONE"
        elif (mode == 1):
            writeDisplay('Router: \nGoogle: ')
            while(mode == 1):
                routeraddr = run_cmd(routercmd)
                pingcmd = "ping -c 1 " + routeraddr.rstrip() + " | grep -oP 'time=\K.*'"
                if (len(routeraddr)>0):
                    routerping = run_cmd(pingcmd).rstrip()
                    googleping = run_cmd(googlecmd).rstrip()
                    if (len(routerping)>0):
                        routermessage = 'Router: ' + routerping + '\n'
                    else:
                        routermessage = 'Router: No Resp.\n'
                    if (len(googleping)>0):
                        googlemessage = ('Google: ' + googleping)
                    else:
                        googlemessage = 'Google: No Resp.'
                    if len(routerping)>0 and len(googleping)>0: #both pass
                        writeDisplay(routermessage+googlemessage,[0,1,0])
                    else:
                        writeDisplay(routermessage+googlemessage,[1,0.5,0])
                else:
                    writeDisplay('Router: No Conn.\nGoogle: No Conn.',[1,0,0])
                for x in range(20):
                    if (mode == 1):
                        sleep(.1)
        elif (mode == 2):
            if (sshran == 0):
                remoteSSH().start()
                sshran = 1
            writeDisplay('DNS: Checking\nTCP: Checking')
            while(mode == 2):
                routeraddr = run_cmd(routercmd)
                if (len(routeraddr)>0):
                    try:
                        response = urllib2.urlopen('http://lucario.info/ok',timeout=10).read()
                    except:
                        response = ""
                        tcpmessage='TCP: Fail'
                        tcpcolor=[1,0,0]
                    if (response == 'Lucario is the best Pokemon!\n'):
                        tcpmessage='TCP: Success'
                        tcpcolor=[0,1,0]
                    else:
                        tcpmessage='TCP: Mismatch'
                        tcpcolor=[1,0.5,0]
                    dns = run_cmd(dnscmd).rstrip()
                    if (dns == "128.172.30.162"):
                        dnsmessage='DNS: Match\n'
                        dnscolor = [0,1,0]
                    elif (len(dns)>0):
                        dnsmessage=dns+'!\n'
                        dnscolor = [1,0.5,0]
                    else:
                        dnsmessage='DNS: No Resp.\n'
                        dnscolor = [1,0,0]
                    writeDisplay(dnsmessage + tcpmessage,list(tcpcolor)) #passing a list requires list()..?
                else:
                    writeDisplay('DNS: No Conn.\nTCP: No Conn.',[1,0,0])
                for x in range(20):
                    if (mode == 2):
                        sleep(.1)
        elif(mode == 3):
            #mac = run_cmd(maccmd).rstrip()
            writeDisplay('VLAN: Checking...\nPort: Checking...')
            if (len(str(vlan))>0):
                vlancolor = [0,1,0]
            else:
                vlancolor = [1,0.5,0]
            while(mode == 3):
                if port == 0:
                    writeDisplay('VLAN: ' + str(vlan).rstrip() + '\n' +'Port: No Conn.',list(vlancolor))
                else:
                    writeDisplay('VLAN: ' + str(vlan).rstrip() + '\n' +'Port:'+str(port).rstrip()[-11:],list(vlancolor))
                for x in range(20):
                    if (mode == 3):
                        sleep(.1)
        elif (mode == 4):
            writeDisplay('Speed: \nDuplex: ')
            while(mode == 4):
                if (isup):
                    portspeed = run_cmd(speedcmd).rstrip()
                    portduplex = run_cmd(duplexcmd).rstrip()
                    if (len(portspeed)>0):
                        if portspeed == "100Mb/s":
                            portspeed = "100Mb/s+"
                        speedmessage = 'Speed: ' + portspeed + '\n'
                    else:
                        speedmessage = 'Speed: No Info\n'
                    if (len(portduplex)>0):
                        duplexmessage = ('Duplex: ' + portduplex)
                    else:
                        duplexmessage = 'Duplex: No Resp.'
                    if len(portspeed)>0 and len(portduplex)>0: #both pass
                        writeDisplay(speedmessage+duplexmessage,[0,1,0])
                    else:
                        writeDisplay(speedmessage+duplexmessage,[1,0.5,0])
                else:
                    writeDisplay('Speed: No Conn.\nDuplex: No Conn.',[1,0,0])
                for x in range(20):
                    if (mode == 4):
                        sleep(.1)
    except:
        quit = 1
        display.queue.put("QUIT") #Refresh the display to end the display thread
        sleep(0.1)
        raise
