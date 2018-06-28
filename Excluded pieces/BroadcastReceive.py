# to bedzie serwer odbierajacy adres klienta i otwierajacy polaczenie

import socket
import subprocess
import time
import os
import platform
import os
systemName = platform.system()

# cross-platform
if systemName == "Windows":
    import wmi  # biblioteka typowa dla Windows

    def getDeviceIP():
        wmi_obj = wmi.WMI()
        wmi_sql = "select IPAddress,DefaultIPGateway from Win32_NetworkAdapterConfiguration where IPEnabled=TRUE"
        wmi_out = wmi_obj.query(wmi_sql)
        return wmi_out[0].IPAddress[0]


    def getMask():
        ip = getDeviceIP()
        proc = subprocess.Popen('ipconfig', stdout=subprocess.PIPE)  # korzysta z cmd
        while True:
            line = proc.stdout.readline()
            if ip.encode() in line:
                break
        mask = proc.stdout.readline().rstrip().split(b':')[-1].replace(b' ', b'').decode()
        return mask


elif systemName == "Linux":
    def getDeviceIP():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # nie musi byc osiagalny
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except socket.error:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    try:
        import netifaces

        print "Netifaces found!"
        def getMask():
            return netifaces.ifaddresses("wlan0")[netifaces.AF_INET][0]['netmask']  # wlan0 jest typowe dla Androida, w Windowsie wystepuje pod inna nazwa
    except ImportError:
        print "Netifaces module not found"

        def getMask():
            ip = getDeviceIP()
            proc = subprocess.Popen('ifconfig', stdout=subprocess.PIPE)
            while True:
                line = proc.stdout.readline()
                if ip.encode() in line:
                    break
            mask = line.rstrip().split(b':')[-1].replace(b' ', b'').decode()
            return mask


else:
    print "NIEOBSLUGIWANY SYSTEM: " + systemName
    os._exit(-1)


def toBin(intVal):
    return "{0:b}".format(intVal).zfill(8)


def toInt(binVal):
    return int(binVal, 2)


def findRange(deviceIP, networkMask):  # zakres poszukiwan serwera
    deviceIPOctets = deviceIP.split(".")
    networkMaskOctets = networkMask.split(".")
    minHost = ""
    maxHost = ""

    for i in range(0, 4):
        currentMaskOctet = toBin(int(networkMaskOctets[i]))  # string
        currentIPOctet = toBin(int(deviceIPOctets[i]))
        networkOctet = ""
        broadcastOctet = ""
        for j in range(0, len(currentMaskOctet)):
            if currentMaskOctet[j] == "1":
                networkOctet += currentIPOctet[j]
                broadcastOctet += currentIPOctet[j]
            else:
                networkOctet += "0"
                broadcastOctet += "1"
        minHost += str(toInt(networkOctet)) + "."
        maxHost += str(toInt(broadcastOctet)) + "."

    minHost = minHost[:len(minHost) - 1]  # usun niepotrzebne kropki na koncu adresu
    maxHost = maxHost[:len(maxHost) - 1]  # !uwzglednia tez network i broadcast adres, ale to tylko o 2 sieci wiecej do sprawdzenia
    result = [minHost, maxHost]
    return result


#####################
receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receiver.bind(("", 8889))

#  sprawdzenie we while, czy prawidlowa wiadomosc
message = receiver.recv(1024)
print message

serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverSocket.connect((message, 8890))

print "Connection established!"
#####################
