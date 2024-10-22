from socket import *
import threading
import select
from colorama import Fore, init

init()


# Client side of peer
class PeerClient(threading.Thread):
    # variable initializations for the client side of the peer
    def __init__(self, ipToConnect, portToConnect, username, peerServer, responseReceived):
        threading.Thread.__init__(self)
        # keeps the ip address of the peer that this will connect
        self.ipToConnect = ipToConnect
        # keeps the username of the peer
        self.username = username
        # keeps the port number that this client should connect
        self.portToConnect = portToConnect
        # client side tcp socket initialization
        self.tcpClientSocket = socket(AF_INET, SOCK_STREAM)
        # keeps the server of this client
        self.peerServer = peerServer
        # keeps the phrase that is used when creating the client
        # if the client is created with a phrase, it means this one received the request
        # this phrase should be none if this is the client of the requester peer
        self.responseReceived = responseReceived
        # keeps if this client is ending the chat or not
        self.isEndingChat = False
        self.clientChattingClients = []
        self.timer = None

    def setChattingClients(self, peerServers):
        self.clientChattingClients.append(peerServers)

    # main method of the peer client thread
    def run(self):
        # connects to the server of other peer
        self.tcpClientSocket.connect((self.ipToConnect, self.portToConnect))
        # if the server of this peer is not connected by someone else and if this is the requester side peer client
        # then enters here
        if self.peerServer.isChatRequested == 0 and self.responseReceived is None:
            # composes a request message and this is sent to server and then this waits a response message from the
            # server this client connects
            requestMessage = "CHAT-REQUEST " + str(self.peerServer.peerServerPort) + " " + self.username
            # sends the chat request
            try:
                self.tcpClientSocket.send(requestMessage.encode())
            except ConnectionError:
                pass
            print(Fore.LIGHTGREEN_EX + "Request message " + requestMessage + " is sent...")
            print(Fore.LIGHTBLACK_EX, end="")
            # received a response from the peer which the request message is sent to
            self.tcpClientSocket.setblocking(False)  # Set socket to non-blocking mode
            ready = select.select([self.tcpClientSocket], [], [], 60)  # Wait for 1 minute for data to be available

            if ready[0]:
                self.responseReceived = self.tcpClientSocket.recv(1024).decode()
            else:
                print(
                    Fore.RED + "No response received within 1 minutes." + Fore.LIGHTBLACK_EX)
                self.responseReceived = "REJECT"
                requestMessage = "TIMEOUT"

                try:
                    # sends the chat request
                    self.tcpClientSocket.send(requestMessage.encode())
                except ConnectionError:
                    pass
            # parses the response for the chat request
            self.responseReceived = self.responseReceived.split()
            # if response is ok then incoming messages will be evaluated as client messages and will be sent to the
            # connected server
            if self.responseReceived[0].upper() == "OK":
                # changes the status of this client's server to chatting
                self.peerServer.isChatRequested = 1
                # sets the server variable with the username of the peer that this one is chatting
                self.peerServer.chattingClientName = self.responseReceived[1]
                print(Fore.LIGHTGREEN_EX + f"{self.peerServer.chattingClientName} accepted the request"
                      + Fore.LIGHTBLACK_EX)
                self.peerServer.timerFunction()
                self.sendOnlineMessage()
                # as long as the server status is chatting, this client can send messages
                while self.peerServer.isChatRequested == 1:
                    # message input prompt
                    messageSent = input(Fore.LIGHTBLACK_EX)
                    # sends the message to the connected peer
                    try:
                        self.tcpClientSocket.send(messageSent.encode())
                    except ConnectionError:
                        pass
                    # if the quit message is sent, then the server status is changed to not chatting
                    # and this is the side that is ending the chat
                    if messageSent == ":q":
                        self.peerServer.isChatRequested = 0
                        self.isEndingChat = True
                        break
                # if peer is not chatting, checks if this is not the ending side
                if self.peerServer.isChatRequested == 0:
                    if not self.isEndingChat:
                        # tries to send a quit message to the connected peer
                        try:
                            self.tcpClientSocket.send(":q ending-side".encode())
                        except ConnectionError:
                            pass
                    # closes the socket
                    self.responseReceived = None
                    self.tcpClientSocket.close()
            # if the request is rejected, then changes the server status, sends a reject message to the connected
            elif self.responseReceived[0].upper() == "REJECT":
                self.peerServer.isChatRequested = 0
                print(Fore.RED + "client of requester is closing...")
                print(Fore.LIGHTBLACK_EX, end="")
                try:
                    self.tcpClientSocket.send("REJECT".encode())
                except ConnectionError:
                    pass
                self.tcpClientSocket.close()
            # if a busy response is received, closes the socket
            elif self.responseReceived[0] == "BUSY":
                print(Fore.RED + "Receiver peer is busy")
                print(Fore.LIGHTBLACK_EX, end="")
                self.tcpClientSocket.close()
        # if the client is created with OK message it means that this is the client of receiver side peer, so it sends
        # an OK message to the requesting side peer server that it connects and then waits for the user inputs.
        elif self.responseReceived.upper() == "OK":
            # server status is changed
            self.peerServer.isChatRequested = 1
            # ok response is sent to the requester side
            okMessage = "OK"
            try:
                self.tcpClientSocket.send(okMessage.encode())
            except ConnectionError:
                pass
            print(Fore.LIGHTGREEN_EX + "Client with OK message is created... and sending messages")
            print(Fore.LIGHTBLACK_EX, end="")
            self.peerServer.timerFunction()
            self.sendOnlineMessage()
            # client can send messages as long as the server status is chatting
            while self.peerServer.isChatRequested == 1:
                # input prompt for user to enter message
                messageSent = input(Fore.LIGHTBLACK_EX)
                try:
                    self.tcpClientSocket.send(messageSent.encode())
                except ConnectionError:
                    pass
                # if a quit message is sent, server status is changed
                if messageSent == ":q":
                    self.peerServer.isChatRequested = 0
                    self.isEndingChat = True
                    break
            # if server is not chatting, and if this is not the ending side
            # sends a quitting message to the server of the other peer
            # then closes the socket
            if self.peerServer.isChatRequested == 0:
                if not self.isEndingChat:
                    try:
                        self.tcpClientSocket.send(":q ending-side".encode())
                    except ConnectionError:
                        pass
                self.responseReceived = None
                self.tcpClientSocket.close()

        elif self.responseReceived == "CHAT-ROOM":
            self.peerServer.isChatRequested = True
            self.isEndingChat = False
            socketsArray = []

            socketsArray.clear()
            registryName = gethostbyname(gethostname())
            registryPort = 15600
            tcpClientSocket1 = socket(AF_INET, SOCK_STREAM)
            tcpClientSocket1.connect((registryName, registryPort))

            message = "GET-COLOR"
            tcpClientSocket1.send(message.encode())

            random_color = tcpClientSocket1.recv(1024).decode()

            tcpClientSocket1.close()

            self.updateClients(socketsArray)

            for server in self.clientChattingClients:
                if not(server[0] == self.peerServer.peerServerHostname and server[1] == self.peerServer.peerServerPort):
                    socketsArray.append(socket(AF_INET, SOCK_STREAM))
                    socketsArray[-1].connect((server[0], server[1]))
                    message = "JOIN-CHAT-ROOM " + self.peerServer.peerServerHostname + " " + str(
                        self.peerServer.peerServerPort) + " " + self.username + " " + random_color
                    socketsArray[-1].send(message.encode())

            while not self.isEndingChat:
                # message input prompt
                messageSent = input(Fore.LIGHTBLACK_EX)
                self.updateClients(socketsArray)

                if messageSent == ":q":
                    self.peerServer.isChatRequested = 0
                    for socketElement in socketsArray:
                        try:
                            self.isEndingChat = True
                            message = "LEAVE-CHAT-ROOM " + self.peerServer.peerServerHostname + " " + str(
                                self.peerServer.peerServerPort) + " " + self.username + " " + random_color + " "
                            socketElement.send(message.encode())
                            socketElement.close()
                            self.peerServer.serverChattingClients.clear()

                        except ConnectionError:
                            socketsArray.remove(socketElement)
                    socketsArray.clear()
                    registryName = gethostbyname(gethostname())
                    registryPort = 15600
                    tcpClientSocket1 = socket(AF_INET, SOCK_STREAM)
                    tcpClientSocket1.connect((registryName, registryPort))

                    message = "LEAVE_CHAT_ROOM " + self.username
                    tcpClientSocket1.send(message.encode())

                    tcpClientSocket1.close()
                    return
                else:
                    for socketElement in socketsArray:
                        try:
                            socketElement.send((self.username + "#%#" + messageSent + "#%#" + random_color).encode())
                        except ConnectionError:
                            # print(random_color + "User left the chat room")
                            socketsArray.remove(socketElement)
                        except Exception as ex:
                            print(Fore.RED + f"An error occurred: {ex}")
                            print(Fore.LIGHTBLACK_EX, end="")

            # closes the socket
            for socketElement in socketsArray:
                socketElement.close()
                socketsArray.remove(socketElement)
            self.responseReceived = None

    def updateClients(self, socketsArray):
        if len(self.clientChattingClients) == len(self.peerServer.serverChattingClients):
            for index in range(len(self.clientChattingClients)):
                if self.clientChattingClients[index] != self.peerServer.serverChattingClients[index]:
                    self.clientChattingClients.clear()
                    for chatting_client in self.peerServer.serverChattingClients:
                        self.setChattingClients(chatting_client)
                    socketsArray.clear()
                    for server in self.clientChattingClients:
                        if not(server[0] == self.peerServer.peerServerHostname and
                               server[1] == self.peerServer.peerServerPort):
                            socketsArray.append(socket(AF_INET, SOCK_STREAM))
                            socketsArray[-1].connect((server[0], server[1]))
                            break
        else:
            self.clientChattingClients.clear()
            for chatting_client in self.peerServer.serverChattingClients:
                self.setChattingClients(chatting_client)
            socketsArray.clear()
            for server in self.clientChattingClients:
                if not(server[0] == self.peerServer.peerServerHostname and server[1] == self.peerServer.peerServerPort):
                    socketsArray.append(socket(AF_INET, SOCK_STREAM))
                    socketsArray[-1].connect((server[0], server[1]))

    def sendOnlineMessage(self):
        if self.peerServer.isChatRequested:
            try:
                message = "$&$& " + self.username
                self.tcpClientSocket.send(message.encode())
                self.timer = threading.Timer(1, self.sendOnlineMessage)
                self.timer.start()
            except ConnectionError:
                pass
