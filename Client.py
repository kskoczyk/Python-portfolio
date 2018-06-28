import socket
import pickle
import subprocess
import json
import time
import jsonpickle
import sys
import os
import platform
systemName = platform.system()
#systemName = "Linux"

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


def howManyHosts(mask):
    maskOctets = mask.split(".")
    maskString = ""
    for i in range (0, 4):
        maskString += toBin(int(maskOctets[i]))

    maskCount = 0
    for i in range(0, 32):
        if maskString[i] == "1":
            maskCount += 1
        else:
            break

    return 2**(32 - maskCount)


def findConnection(port, minRange, maxRange, maxHosts):
    minRangeOctets = minRange.split(".")
    maxRangeOctets = maxRange.split(".")

    counter = 0
    testAddress = ""  # aktualnie sprawdzany adres pod katem wystepowania serwera
    for a in range(int(minRangeOctets[0]), int(maxRangeOctets[0]) + 1):
        for b in range(int(minRangeOctets[1]), int(maxRangeOctets[1]) + 1):
            for c in range(int(minRangeOctets[2]), int(maxRangeOctets[2]) + 1):
                for d in range(int(minRangeOctets[3]), int(maxRangeOctets[3]) + 1):
                    print counter, "/", maxHosts, " przeszukano"
                    counter += 1
                    testAddress = str(a) + "." + str(b) + "." + str(c) + "." + str(d)
                    try:
                        host = testAddress
                        # print "Connecting with " + host + ". . ."
                        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        serverSocket.settimeout(0.2)
                        serverSocket.connect((host, port))
                    except socket.timeout:
                        # print "TIMED OUT"
                        continue
                    except socket.error:
                        # print "SOCKET ERROR"
                        continue

                    # znaleziono otwarty socket - rozpocznij przywitanie
                    try:
                        serverSocket.send("TRUECLIENT")
                        serverSocket.settimeout(2)  # dluzszy czas odpowiedzi na handshake
                        handshake = serverSocket.recv(1024)
                        if handshake != "TRUESERVER":
                            print "Invalid handshake: " + handshake
                            continue  # nieprawidlowy serwer
                    except socket.error:
                        print "Socket error"
                        continue
                    print "SUCCESS " + "Znaleziono polaczenie pod: " + testAddress
                    return serverSocket

    return None


def sendBroadcast(broadcast, port):
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sender.settimeout(1)
    contact = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    contact.bind(("", port+2))  # opakowac w try, niech czeka, az inny klient zwolni socket
    contact.listen(10)
    contact.settimeout(1)

    serverIP = None
    for i in range(0, 15):
        sender.sendto(getDeviceIP(), (broadcast, port+1))
        try:
            connection = contact.accept()
            print "Nawiazano polaczenie! Z: ", connection[1]
            serverIP = connection[1][0]  # odbieranie danych nie dziala pomiedzy platformami, error 10035
            #connection[0].send(getDeviceIP())
        except socket.timeout:
            print "."
            continue
        break

    if serverIP is not None:
        return findConnection(port, serverIP, serverIP, 1)
    else:
        return None


def toBin(intVal):
    return "{0:b}".format(intVal).zfill(8)


def toInt(binVal):
    return int(binVal, 2)


deviceIP = getDeviceIP()
mask = getMask()
maxHosts = howManyHosts(mask)
print deviceIP
print mask
port = 8888
size = 1024
# znalezc legitnie adres i maske
ranges = findRange(deviceIP, mask)
print ranges[0]
print ranges[1]
print "Szukanie serwera..."
server = None
# try:
server = sendBroadcast(ranges[1], port)
# except socket.error:
#     print "Port jest zajety. Czy istnieje kilka klientow korzystajacych z tego samego adresu IP?"
if server is None:
    print "Nie odnaleziono serwera. Byc moze serwer jest offline lub konfiguracja sieci uniemozliwia broadcasting"
    print "Przechodze do manualnej metody (to moze troche potrwac)"
    server = findConnection(port, ranges[0], ranges[1], maxHosts) # moze byc jedn adres

# obsluz None

# for i in range(0, 255):
#     try:
#         host = starthost + str(i)
#         # print "Connecting with " + host + ". . ."
#         server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         server.settimeout(0.0001)
#         server.connect((host, port))
#     except socket.timeout:
#         # print "TIMED OUT"
#         continue
#     except socket.error:
#         # print "SOCKET ERROR"
#         continue
#     print "SUCCESS"
#     break

if server is None:
    print "Serwer jest offline"
    os._exit(-1)
server.settimeout(None)
choice = ""
while 1:
    print "1. Nowe zadanie"
    print "2. Wyswietl wszystkie zadania"
    print "3. Wyswietl zadania o wskazanym priorytecie"
    print "4. Zapisz do pliku"
    print "5. Usun zadanie"
    print "6. Znajdz sieci wifi po stronie serwera"
    print "7. Rozlacz"
    choice = input()
    if choice == 1:
        priorytet = raw_input("Podaj priorytet zadania: ")
        nazwa = raw_input("Podaj nazwe zadania: ")
        tempID = -1     # chwilowe ID, zmieni je serwer
        newTask = [tempID, priorytet, nazwa]
        dataStream = pickle.dumps(newTask)
        print "Tworze nowe zadanie. . ."
        server.send("add")
        server.send(dataStream)
        isSuccess = server.recv(size)
        if isSuccess == "0":
            print "Pomyslnie utworzono zadanie!"
        else:
            print "Nie udalo sie utworzyc zadania."
    elif choice == 2:
        print "Wczytuje zadania. . ."
        server.send("showAll")
        taskBaseDataStream = server.recv(size)
        receivedTaskBase = pickle.loads(taskBaseDataStream)
        print receivedTaskBase
    elif choice == 3:
        server.send("showPriority")
        showPriority = raw_input("Podaj priorytet zadan do wyswietlenia: ")
        server.send(showPriority)
        receivedListStream = server.recv(size)
        receivedList = pickle.loads(receivedListStream)
        print receivedList
    elif choice == 4:
        print "Wysylam zadanie zapisania bazy zadan. . ."
        server.send("saveToFile")
        isSuccess = server.recv(size)
        if isSuccess == "0":
            print "Zapisywanie zakonczone powodzeniem!"
    elif choice == 5:
        deleteID = raw_input("Podaj ID zadania do usuniecia: ")
        print "Usuwam zadanie o ID " + deleteID + ". . ."
        server.send("delete")
        server.send(deleteID)
        isSuccess = server.recv(size)
        if isSuccess == "0":
            print "Usuwanie zakonczone powodzeniem!"
        else:
            print "Nie udalo sie usunac zadania o ID " + deleteID + ". Czy takie zadanie isnieje?"
    elif choice == 6:
        server.send("listWifi")
        wifiPickle = server.recv(size)
        wifiList = pickle.loads(wifiPickle)
        print "Lista sieci wifi znalezionych przez serwer: "
        for wifiTuple in wifiList:
            print wifiTuple
    elif choice == 7:
        print "Rozlaczam. . ."
        server.send("disconnect")
        isSuccess = server.recv(size)
        if isSuccess == "0":
            print "Bezpiecznie rozlaczono!"
        server.close()
        os._exit(0)
    else:
        print "Nie ma takiej opcji"


server.close()
print 'Czas serwera: ', tm
###############
# from socket import *
# serwer = socket(AF_INET, SOCK_STREAM) #utworzenie gniazda
# serwer.connect(('localhost', 8888)) # nawiazanie polaczenia
# # tm = s.recv(1024) #odbior danych (max 1024 bajtow)
#
# wybor = ""
# while 1:
#     print "1. Nowe zadanie"
#     print "2. Wyswietl zadania"
#     print "3. Wylacz sewer"
#     wybor = input()
#     if wybor == 1:          #tworzenie nowego zadania
#         print "Tworze nowe zadanie"
#         priorytet = raw_input("Podaj priorytet zadania: ")
#         nazwa = raw_input("Podaj nazwe zadania: ")
#         zadanie = priorytet + "," + nazwa
#         serwer.send("dodaj_zadanie")
#         serwer.send(zadanie)
#     elif wybor == 2:
#         print "Wyswietlam zadania"
#         serwer.send("wyswietl_zadania")
#         zadania = serwer.recv(1024)
#         print  zadania
#     elif wybor == 3:
#         print "Zamykam serwer"
#         serwer.send("zamknij_serwer")
#     else:
#         print "Nie ma takiej opcji"
#
#
# s.close()
# print 'Czas serwera: ', tm