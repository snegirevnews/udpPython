from twisted.internet.protocol import Protocol, Factory, DatagramProtocol
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.internet.task import LoopingCall
from functools import partial

import cryptotools as cryptotools
import messages as messages
from time import time
# import chechBlock as chechBlock
# import BlockDB as DB


PING_INTERVAL = 1200.0 #каждые 20 минут я проверяю на активность
CorrectAnswer = 'NO'

class MyProtocol(Protocol):
    def __init__(self, factory, state="GETHELLO", kind="LISTENER"):
        self.factory = factory
        self.state = state
        self.VERSION = 0
        self.remote_nodeid = None
        self.kind = kind
        self.nodeid = self.factory.nodeid #Идентификационный номер отправителя
        self.lc_ping = LoopingCall(self.send_PING)


        #При подключении нового нода (прокидываю порты, вроде)
    def connectionMade(self):
        remote_ip = self.transport.getPeer()
        host_ip = self.transport.getHost()
        self.remote_ip = remote_ip.host + ":" + str(remote_ip.port)
        self.host_ip = host_ip.host + ":" + str(host_ip.port)
        print ("Connection from", self.transport.getPeer())

        #При потере соединения с нодом
    def connectionLost(self, reason):
        try:
            self.lc_ping.stop()
        except AssertionError:
            pass

        try:
            self.factory.peers.pop(self.remote_nodeid)
        except KeyError:
            if self.nodeid != self.remote_nodeid:
                print(" [ ] GHOST LEAVES: from", self.remote_nodeid, self.remote_ip)

        #Анализирую полученныый протокол на тип сообщения
    def dataReceived(self, data):
        for line in data.splitlines():
            line = line.strip()
            envelope = messages.read_envelope(line)
            if self.state in ["GETHELLO", "SENTHELLO"]:
                if envelope['msgtype'] == 'hello':
                    self.handle_HELLO(line)
                else:
                    print(" [!] Ignoring", envelope['msgtype'], "in", self.state)
            else:
                if envelope['msgtype'] == 'ping':
                    self.handle_PING(line)
                elif envelope['msgtype'] == 'pong':
                    self.handle_PONG(line)
                elif envelope['msgtype'] == 'addr':
                    self.handle_ADDR(line)
                # elif envelope['msgtype'] == 'getBlock':
                #     self.handle_BLOCK(line)
                # elif envelope['msgtype'] == 'checkAuth':
                #     self.handle_AUTH(line)
                # elif envelope['msgtype'] == 'correct':
                #     self.handle_CORRECT(line)
                # elif envelope['msgtype'] == 'filter':
                #     self.handle_SEARCH(line)
                # elif envelope['msgtype'] == 'searchResult':
                #     self.handle_SEARCHRESULT(line)

        #Отправка "Приветственного сообщения", чтобы другие ноды узнали обо мне
    def send_HELLO(self):
        hello = messages.create_hello(self.nodeid, self.VERSION)
        self.sendLine(hello+ "\n")
        self.state = "SENTHELLO" #состояние SENTHELLO
        print("SEND_HELLO:", self.nodeid, "to", self.remote_ip)

        #При получении "Приветственного сообщени" запоминаю пира, и знакомлю его со своими
    def handle_HELLO(self, hello):
        try:
            print("Получил HELLO")
            hello = messages.read_message(hello)
            self.remote_nodeid = hello['nodeid'] #nodeid того,кто прислал письмо

            if self.remote_nodeid == self.nodeid: #если я  сам себе прислал
                print(" [!] Found myself at", self.host_ip)
                self.transport.loseConnection()

            else: #если я не сам себе прислал
                if self.state == "GETHELLO": #если я в состоянии GETHELLO
                    my_hello = messages.create_hello(self.nodeid, self.VERSION) #собираю свое Hello- сообщение
                    self.sendLine(my_hello + "\n") #отправляю

                self.add_peer() # добавить данный пир в List
                self.state = "READY" #ставлю себе состояние READY

                if self.kind == "LISTENER": #если я СЛУШАЮ, то начинаю пинговать Пира
                    print(" [ ] Starting pinger to " + self.remote_nodeid)
                    self.lc_ping.start(PING_INTERVAL, now=False)
                    # Рассказываю данному ноду о моих пирах.
                    self.send_ADDR()

        except messages.InvalidSignatureError: #если в ходе передачи были искажены данные
            print(" [!] ERROR: Invalid hello sign ", self.remoteip)
            self.transport.loseConnection()


        #Добавление Ip,Port в Лист, а также Объекта типа сокет в другой Лист
    def add_peer(self): #добавление Пира в Лист
        entry = (self.remote_ip, self.kind, time())
        self.factory.peers[self.remote_nodeid] = entry
        self.factory.peers_protocol[self.remote_nodeid] = self


        # Рассказываю данному ноду о моих пирах.
    def send_ADDR(self):
        peers = self.factory.peers
        listeners = [(n, peers[n][0], peers[n][1], peers[n][2])
                     for n in peers]
        addr = messages.create_addr(self.nodeid, listeners)
        self.sendLine(addr)
        print("Telling " + self.remote_nodeid + " about my peers")


        #Получил адреса других пиров от нода.
    def handle_ADDR(self, addr):
        try:
            nodes = messages.read_message(addr)['nodes']
            print("Recieved addr list from peer " + self.remote_nodeid)
            for node in nodes:
                print(" " + node[0] + " " + node[1])
                if node[0] == self.nodeid:
                    print(" [!] Not connecting to " + node[0] + ": thats me!")
                    return
                if node[1] != "SPEAKER":
                    print(" [ ] Not connecting to " + node[0] + ": is " + node[1])
                    return
                if node[0] in self.factory.peers:
                    print(" [ ] Not connecting to " + node[0] + ": already connected")
                    return
                print(" [ ] Trying to connect to peer " + node[0] + " " + node[1])
                host, port = node[0].split(":")
                point = TCP4ClientEndpoint(reactor, host, int(port))
                d = connectProtocol(point, MyProtocol(self.factory, "SENDHELLO", "SPEAKER"))
                d.addCallback(gotProtocol)
        except messages.InvalidSignatureError:
            print (addr)
            print("ERROR: Invalid addr sign ", self.remote_ip)
            self.transport.loseConnection()

        #Отправляю ПИНГ сообщени
    def send_PING(self):
        print("PING   to", self.remote_nodeid, "at", self.remote_ip)
        ping = messages.create_ping(self.nodeid)
        self.sendLine(ping)

        # Если получил ПИНГ сообщени, то посылаем ПОНГ
    def handle_PING(self, ping):
        if messages.read_message(ping):
            pong = messages.create_pong(self.nodeid)
            self.sendLine(pong)

        #Если было получено ПОНГ сообщение, обновляем информацию.
    def handle_PONG(self, pong):
        pong = messages.read_message(pong)
        print("PONG from", self.remote_nodeid, "at", self.remote_ip)
        addr, kind = self.factory.peers[self.remote_nodeid][:2]
        self.factory.peers[self.remote_nodeid] = (addr, kind, time())

        #Пришел новый блок
    # def handle_BLOCK(self, block):
    #     print("GET BLOCK")
    #     blc= messages.read_message(block)
    #     blc=blc['block']
    #     if (chechBlock.CheckBlockValid(blc)):
    #         pass

        # Пришли авторизационные данные
    # def handle_AUTH(self, auth):
    #     print("GET AUTH")
    #     authData = messages.read_message(auth)
    #     authData = authData['auth']
    #     print(authData)
    #     authData = DB.chechAuthCode(authData)
    #
    #     if (len(authData) > 0):
    #         print('YES,AUTH')
    #         self.send_CORRECT('YES')
    #     else: self.send_CORRECT('NO')

    # def send_CORRECT(self,correct):
    #     addr = messages.send_correct(self.nodeid, correct)
    #     self.sendLine(addr)
    #
    # def handle_CORRECT(self, correct):
    #     correctData = messages.read_message(correct)
    #     correctData = correctData['correct']
    #     if(correctData == 'YES'):
    #         CorrectAnswer = 'YES'
    #         MainObj.getAuthAnswer(CorrectAnswer)
    #     elif(correctData == 'NO'):
    #         CorrectAnswer = 'NO'
    #         MainObj.getAuthAnswer(CorrectAnswer)
    #
    # def handle_SEARCH(self, filter):
    #     filter = messages.read_message(filter)
    #     filter = filter['filter']
    #     print(filter)
    #     res= DB.searchFilter(filter)
    #     self.send_SEARCH(res)
    #
    # def send_SEARCH(self,res):
    #     result= messages.send_searchResult(self.nodeid, res)
    #     self.sendLine(result)
    #
    # def handle_SEARCHRESULT(self, result):
    #     MainObj.recvResult(result)

        #Метод отправки сформированного протокола
    def sendLine(self, line):
        self.transport.write(line.encode('utf8'))

class MyFactory(Factory):
    def __init__(self):
        pass

    def startFactory(self):
        self.peers = {}
        self.peers_protocol = {}
        self.numProtocols = 0
        self.nodeid = cryptotools.generate_nodeid()[:10]
        print(" [ ] NODEID:", self.nodeid)

    def stopFactory(self):
        pass

    def mainObj(self,obj):
        global MainObj
        MainObj = obj

    def buildProtocol(self, addr):
        return MyProtocol(self, "GETHELLO", "LISTENER")

    def sendBlockToAll(self, block):
        for key, peer in self.peers_protocol.items():
            blc= messages.create_block(self.nodeid, block)
            peer.sendLine(blc)

    def sendAuthToAll(self, auth):
        for key, peer in self.peers_protocol.items():
            authMessage = messages.chech_auth(self.nodeid, auth)
            peer.sendLine(authMessage)

    def search(self, filter):
        for key, peer in self.peers_protocol.items():
            searchMessage = messages.search(self.nodeid, filter)
            peer.sendLine(searchMessage)

def gotProtocol(p):
    p.send_HELLO()

class UDPClientProtocol(DatagramProtocol):
    def __init__(self):
       self.peers = {}
       self.nodeid = cryptotools.generate_nodeid()[:10]

    def startProtocol(self):
       # Called when transport is connected
       print('LISTEN')

    def datagramReceived(self, data, addr):
        print ("received %r from %s" % (data, addr))
        entry = (addr[0],addr[1])
        print(entry)
        print(data.decode())
        self.peers[data.decode()] = entry
        peers = self.peers
        listeners = [(n, peers[n][0], peers[n][1])
                     for n in peers]
        addres = messages.create_addr(self.nodeid, listeners)
        self.transport.write(addres.encode(), addr)


    def stopProtocol(self):
       print ("I have lost connection and self.transport is gone!")
       # wait some time and try to reconnect somehow?

    # Possibly invoked if there is no server listening on the
    # address to which we are sending.
    def connectionRefused(self):
        print ("No one listening")