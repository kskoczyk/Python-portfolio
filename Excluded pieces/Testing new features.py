#listuj sieci WiFi

import subprocess
import wifi
import pickle
import socket
import wmi
results = subprocess.check_output(["netsh", "wlan", "show", "network"])
#results = results.decode("utf-8") # needed in python 3
results = results.replace("\r", "")
ls = results.split("\n")
ls = ls[4:len(ls)-2] #from 4 to end
print ls
ssids = []
x = 0
while x < len(ls):
    if x % 5 == 0:
        # ssids.append(ls[x].replace(" ", ""))     #nazwa sieci
        # ssids.append(ls[x+2].replace(" ", ""))   #rodzaj uwierzytelniania
        ssids.append((ls[x].replace(" ", ""), ls[x+2].replace(" ", "")))
    x += 1
print len(ssids)
print len(ssids[0])
print(ssids)  # piklowalne
print
# print wifi.Cell.all('wlan0')

# #listuj urzadzenia Bluetooth
# import bluetooth #niesamowicie trudne do zainstalowania pod Windows
#
# print "performing inquiry..."
#
# nearby_devices = bluetooth.discover_devices(lookup_names = True)
#
# print "found %d devices" % len(nearby_devices)
#
# for name, addr in nearby_devices:
#      print " %s - %s" % (addr, name)

#znajdz wspolny adres dla klienta i serwera
# print socket.gethostbyname(socket.gethostname())
# print socket.getfqdn()
#
#
# def get_ip():
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     try:
#         # doesn't even have to be reachable
#         s.connect(('10.255.255.255', 1))
#         IP = s.getsockname()[0]
#     except:
#         IP = '127.0.0.1'
#     finally:
#         s.close()
#     return IP
#
#
# print get_ip()
#
# wmi_obj = wmi.WMI()
# wmi_sql = "select IPAddress,DefaultIPGateway from Win32_NetworkAdapterConfiguration where IPEnabled=TRUE"
# wmi_out = wmi_obj.query( wmi_sql )
# for dev in wmi_out: # liczy sie pierwsze
#     print "IPv4Address:", dev.IPAddress[0], "DefaultIPGateway:", dev.DefaultIPGateway[0]
#
#
# print "Mask:"
# ip = wmi_out[0].IPAddress[0] #Example
# proc = subprocess.Popen('ipconfig', stdout=subprocess.PIPE)
# while True:
#     line = proc.stdout.readline()
#     if ip.encode() in line:
#         break
# mask = proc.stdout.readline().rstrip().split(b':')[-1].replace(b' ',b'').decode()
# print mask
# print "Done"