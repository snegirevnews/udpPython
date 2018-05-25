from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint, TCP4ClientEndpoint
from twisted.internet.error import CannotListenError
from twisted.internet.endpoints import connectProtocol

import p2pClient as p2pClient
from p2pClient import MyFactory, MyProtocol, UDPClientProtocol

ncfactory = MyFactory()
def connect():
    # # host = "52.14.170.246" #адрес сервера
    # host = "localhost"
    # port = 5006 #порт сервера
    #
    # try:
    #     endpoint = TCP4ServerEndpoint(reactor, 5005)
    #     endpoint.listen(ncfactory)
    #     print("LISTEN")
    # except CannotListenError:
    #     print("[!] Address in use")
    #     raise SystemExit

    t = reactor.listenUDP(5006, UDPClientProtocol())
    reactor.run()

if __name__ == "__main__":
    connect()
