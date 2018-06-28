import select
import socket
import subprocess
import sys
import threading
import time
import os
import platform
import pickle
import jsonpickle
import json


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


def findWifi():
    results = subprocess.check_output(["netsh", "wlan", "show", "network"])
    # results = results.decode("utf-8") # needed in python 3
    results = results.replace("\r", "")
    ls = results.split("\n")
    ls = ls[4:len(ls) - 2]  # from 4 to end
    ssids = []
    x = 0
    while x < len(ls):
        if x % 5 == 0:
            # ssids.append(ls[x].replace(" ", ""))     #nazwa sieci
            # ssids.append(ls[x+2].replace(" ", ""))   #rodzaj uwierzytelniania
            ssids.append((ls[x].replace(" ", ""), ls[x + 2].replace(" ", "")))
        x += 1
    return ssids


class Server:
    def __init__(self):
        self.host = getDeviceIP()
        self.port = 8888
        self.backlog = 5    # nieuzywane
        self.size = 1024
        self.server = None
        self.threads = []   # tablica na watki klientow
        self.mainInstance = self    # referencja do tej klasy

        self.receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiver.bind(("", 8889))

    def open_socket(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self.host, self.port))
            self.server.listen(10)
        except socket.error, (value, message):
            if self.server:
                self.server.close()
            print "Could not open socket: " + message
            sys.exit(1)

    def run(self):
        self.open_socket()
        input = [self.server]
        # input = [self.server, sys.stdin]
        # utworzyc nowy watek do nasluchiwania stdin
        runningMain = 1
        r = BroadcastReceiver(self.server, self.receiver, self.mainInstance)
        r.start()
        while runningMain:
            # inputready, outputready, exceptready = select.select(input, [], [])     # niekompatybilne z Windows

            # for s in inputready:

                # if s == self.server:
                    # handle the server socket
                    accept = self.server.accept()
                    c = Client(accept, self.server, self.mainInstance)
                    c.start()
                    self.threads.append(c)  # z racji pewnych komplikacji watki same usuwaja sie z tablicy
                # elif s == sys.stdin:
                #      # handle standard input
                #      junk = sys.stdin.readline()
                #      running = 0
                #
                #     # close all threads

        # self.server.close()
        # for c in self.threads:
        #     c.join()


class Client(threading.Thread):
    def __init__(self, (client, address), server, mainInstance):
        self.server = server
        threading.Thread.__init__(self)
        self.client = client
        self.address = address
        self.size = 1024
        self.taskBase = []    # baza zadan indywidualnie dla kazdego klienta
        self.taskID = 0
        innerList = ["taskID", "priority", "name"]  # do tworzenia listy 2D, pelni role informatora pol
        self.taskBase.append(innerList)
        self.mainInstance = mainInstance

    def run(self):
        running = 1
        # time.sleep(1)
        # print "ACCEPTED"
        handshake = self.client.recv(self.size)
        if handshake != "TRUECLIENT":  # nieprawidlowy klient
            print "Invalid handshake: " + handshake
            running = 0
        #  TODO: poprawic zabezpieczenia
        self.client.send("TRUESERVER")
        print "Connection with", self.address
        #  TODO: klient timeout
        while running:
            choice = self.client.recv(self.size);
            if choice == "add":  # dodawanie zadania do bazy
                taskDataStream = self.client.recv(self.size)
                receivedTask = pickle.loads(taskDataStream)
                receivedTask[0] = self.taskID
                self.taskID += 1
                self.taskBase.append(receivedTask)
                self.client.send("0")
            elif choice == "showAll":
                listToSend = pickle.dumps(self.taskBase)
                self.client.send(listToSend)
                choice = ""
            elif choice == "showPriority":
                priority = self.client.recv(self.size)
                listToSend = []
                for i, task in enumerate(self.taskBase):
                    if self.taskBase[i][1] == priority:
                        listToSend.append(task)
                listToSendStream = pickle.dumps(listToSend)
                self.client.send(listToSendStream)
            elif choice == "saveToFile":
                # jsonDatabase = jsonpickle.encode(self.taskBase)
                # print jsonDatabase
                path = 'taskBase' + str(self.address[0]) + '_' + str(self.address[1]) + '.json'
                print "Created the file" + path
                with open(path, 'w') as outfile:
                    json.dump(self.taskBase, outfile)
                self.client.send("0")
            elif choice == "delete":
                deleteID = self.client.recv(self.size)
                result = -1
                for i, x in enumerate(self.taskBase):
                    if self.taskBase[i][0] == int(deleteID):
                        del self.taskBase[i]
                        result = 0
                self.client.send(str(result))
            elif choice == "listWifi":
                #  na razie niedostepne dla Linux
                wifiList = findWifi()
                listToSend = pickle.dumps(wifiList)
                self.client.send(listToSend)
            elif choice == "disconnect":
                break

        try:
            self.client.send("0")
            self.client.close()
        except socket.error:
            print "Socket error upon disconnecting with client"
        print "Closed the connection with", self.address
        for i, x in enumerate(self.mainInstance.threads): # szukaj watku do usuniecia (samego siebie), ktory zakonczyl polaczenie z klienetem
            if self == x:
                del self.mainInstance.threads[i]
        howManyClientsActive = len(self.mainInstance.threads)
        if howManyClientsActive == 0:
            print "Last client handled, shutting the server down entirely. . ."
            os._exit(0)
            # self.server.close()


class BroadcastReceiver(threading.Thread):  # jakas petla while, zeby dzialal w nieskonczonosc
    def __init__(self, server, receiver, mainInstance):
        threading.Thread.__init__(self)
        self.server = server
        self.mainInstance = mainInstance
        self.receiver = receiver

    def run(self):
        # receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # receiver.bind(("", 8889))

        #  sprawdzenie we while, czy prawidlowa wiadomosc
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print "Broadcast listening . . ."
        while True:
            message = self.receiver.recvfrom(1024)
            print "Broadcast from: ", message[1], ": ", message[0]

            # serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            serverSocket.connect((message[0], 8890))  # nawiazywanie polaczen z uzyciem broadcast przez inny port, poniewaz pierwotny jest wciaz uzywany do bezposrednich polaczen
            print "Broadcast connection established!"
            serverSocket.send(self.mainInstance.host)  # przeslij deviceIP z glownego watku
            try:
                serverSocket.close()
                serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            except socket.error:
                continue



s = Server()
s.run()
######################
# from socket import *
# import time
# serwer = socket(AF_INET, SOCK_STREAM) #utworzenie gniazda
# serwer.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
# serwer.bind(('0.0.0.0', 8888)) #dowiazanie do portu 8888
# serwer.listen(10)
#
# baza_zadan = []
#
# while 1:
# 	client,addr = serwer.accept() # odebranie polaczenia
# 	print 'Polaczenie z ', addr
# 	# client.send(time.ctime(time.time()) + "wiadomosc") # wyslanie danych do klienta
#
# 	while 1:
# 		wybor = client.recv(1024);
# 		if wybor == "dodaj_zadanie":  # dodawanie zadania do bazy
# 			zadanie = client.recv(1024)
# 			baza_zadan.append(zadanie)
# 			wybor = ""
# 		elif wybor == "wyswietl_zadania":
# 			print baza_zadan
# 			zadania = ""
#
# 			for i, x in enumerate(baza_zadan):
# 				zadania  = zadania + baza_zadan[i] + "|"
# 			client.send(zadania)
# 			wybor = ""
# 		elif wybor == "zamknij_serwer":
# 			serwer = ""
# 			break
#
#
# 	client.close()