from socket import *
import threading
import select
from colorama import Fore, init

init()


# Server side of peer
class PeerServer(threading.Thread):

    # Peer server initialization
    def __init__(self, username, peerServerPort):
        threading.Thread.__init__(self)
        # keeps the username of the peer
        self.username = username
        # tcp socket for peer server
        self.tcpServerSocket = socket(AF_INET, SOCK_STREAM)
        # port number of the peer server
        self.peerServerPort = peerServerPort
        # if 1, then user is already chatting with someone
        # if 0, then user is not chatting with anyone
        self.isChatRequested = 0
        # keeps the socket for the peer that is connected to this peer
        self.connectedPeerSocket = None
        # keeps the ip of the peer that is connected to this peer's server
        self.connectedPeerIP = None
        # keeps the port number of the peer that is connected to this peer's server
        self.connectedPeerPort = None
        # online status of the peer
        self.isOnline = True
        # keeps the username of the peer that this peer is chatting with
        self.chattingClientName = None
        self.serverChattingClients = []
        self.counter = 0

    def setServerChattingClients(self, arrayOfClients):
        self.serverChattingClients.append(arrayOfClients)

    # main method of the peer server thread
    def run(self):
        # gets the ip address of this peer
        # first checks to get it for Windows devices
        # if the device that runs this application is not windows
        # it checks to get it for macOS devices
        hostname = gethostname()
        try:
            self.peerServerHostname = gethostbyname(hostname)
        except gaierror:
            import netifaces as ni
            self.peerServerHostname = ni.ifaddresses('en0')[ni.AF_INET][0]['addr']

        # ip address of this peer
        # self.peerServerHostname = 'localhost'
        # socket initializations for the server of the peer
        self.tcpServerSocket.bind((self.peerServerHostname, self.peerServerPort))
        self.tcpServerSocket.listen(4)
        # inputs sockets that should be listened
        inputs = [self.tcpServerSocket]
        # server listens as long as there is a socket to listen in the inputs list and the user is online
        while inputs and self.isOnline:
            # monitors for the incoming connections
            try:
                readable, writable, exceptional = select.select(inputs, [], [])
                # If a server waits to be connected enters here
                for s in readable:
                    # if the socket that is receiving the connection is
                    # the tcp socket of the peer's server, enters here
                    if s is self.tcpServerSocket:
                        # accepts the connection, and adds its connection socket to the inputs list
                        # so that we can monitor that socket as well
                        connected, addr = s.accept()
                        connected.setblocking(0)
                        inputs.append(connected)
                        # if the user is not chatting, then the ip and the socket of
                        # this peer is assigned to server variables
                        if self.isChatRequested == 0:
                            self.connectedPeerSocket = connected
                            self.connectedPeerIP = addr[0]
                    # if the socket that receives the data is the one that
                    # is used to communicate with a connected peer, then enters here
                    else:
                        if self.counter >= 3:
                            messageReceived = ":q"
                            self.counter = 0
                        else:
                            # message is received from connected peer
                            messageReceived = s.recv(1024).decode()
                        # if message is a request message it means that this is the receiver side peer server
                        # so evaluate the chat request
                        if len(messageReceived) > 11 and messageReceived[:12] == "CHAT-REQUEST":
                            # text for proper input choices is printed however OK or REJECT is taken as input in main
                            # process of the peer if the socket that we received the data belongs to the peer that we
                            # are chatting with, enters here
                            if s is self.connectedPeerSocket:
                                # parses the message
                                messageReceived = messageReceived.split()
                                # gets the port of the peer that sends the chat request message
                                self.connectedPeerPort = int(messageReceived[1])
                                # gets the username of the peer sends the chat request message
                                self.chattingClientName = messageReceived[2]
                                # prints prompt for the incoming chat request
                                print(
                                    Fore.LIGHTGREEN_EX + "Incoming chat request from " + self.chattingClientName)
                                print("Enter OK to accept or REJECT to reject:  " + Fore.LIGHTBLACK_EX)
                                # makes isChatRequested = 1 which means that peer is chatting with someone
                                self.isChatRequested = 1
                                self.counter = 0
                            # if the socket that we received the data does not belong to the peer that we are
                            # chatting with and if the user is already chatting with someone else(isChatRequested =
                            # 1), then enters here
                            elif s is not self.connectedPeerSocket and self.isChatRequested == 1:
                                # sends a busy message to the peer that sends a chat request when this peer is
                                # already chatting with someone else
                                message = "BUSY"
                                s.send(message.encode())
                                # remove the peer from the inputs list so that it will not monitor this socket
                                inputs.remove(s)

                        elif messageReceived == "TIMEOUT":
                            self.isChatRequested = 0
                            inputs.remove(s)
                            print(Fore.RED + "Time-Out" + Fore.LIGHTBLACK_EX)
                            print(Fore.BLUE, end='')
                            print("Choose: \n" + Fore.LIGHTBLUE_EX + "1 Logout\n2 Search\n3 Start a chat\n4 List online users\n5 "
                                                                   "Create a chat room\n6 List chat rooms\n7 Join chat room")
                            print(Fore.LIGHTBLACK_EX, end='')

                        elif messageReceived.startswith("JOIN-CHAT-ROOM"):
                            messageReceived = messageReceived.split(" ")
                            self.serverChattingClients.append([messageReceived[1], int(messageReceived[2])])
                            print(
                                messageReceived[4] + f"{messageReceived[3]} joined the chat room" + Fore.LIGHTBLACK_EX)

                        elif messageReceived.startswith("LEAVE-CHAT-ROOM"):
                            messageReceived = messageReceived.split(" ")
                            for index, client in reversed(list(enumerate(self.serverChattingClients))):
                                if client[0] == messageReceived[1] and client[1] == int(messageReceived[2]):
                                    del self.serverChattingClients[index]
                            print(messageReceived[4] + f"{messageReceived[3]} left the chat room" + Fore.LIGHTBLACK_EX)
                        # if an OK message is received then ischatrequested is made 1 and then next messages will be
                        # shown to the peer of this server
                        elif messageReceived.upper() == "OK":
                            self.isChatRequested = 1
                            self.counter = 0
                        # if an REJECT message is received then ischatrequested is made 0 so that it can receive any
                        # other chat requests
                        elif messageReceived.upper() == "REJECT":
                            self.isChatRequested = 0
                            inputs.remove(s)
                        elif messageReceived.startswith("$&$&"):
                            messageReceived = messageReceived.split(" ")
                            if messageReceived[1] == self.chattingClientName:
                                self.counter = 0
                        # if a message is received, and if this is not a quit message ':q' and
                        # if it is not an empty message, show this message to the user
                        elif messageReceived[:2] != ":q" and len(messageReceived) != 0 and self.isChatRequested == 1:
                            if "#%#" in str(messageReceived):
                                messageReceived = messageReceived.split("#%#")
                                print(messageReceived[2] + messageReceived[0] + ": " + messageReceived[
                                    1] + Fore.LIGHTBLACK_EX)
                            else:
                                print(
                                    Fore.GREEN + self.chattingClientName + ": " + Fore.WHITE + messageReceived +
                                    Fore.LIGHTBLACK_EX)
                        # if the message received is a quit message ':q',
                        # makes ischatrequested 1 to receive new incoming request messages
                        # removes the socket of the connected peer from the inputs list
                        elif messageReceived[:2] == ":q" and self.isChatRequested == 1:
                            self.isChatRequested = 0
                            inputs.clear()
                            inputs.append(self.tcpServerSocket)
                            # connected peer ended the chat
                            print(Fore.RED + "User you're chatting with ended the chat")
                            print("Press enter to quit the chat: " + Fore.LIGHTBLACK_EX)

                        # if the message is an empty one, then it means that the
                        # connected user suddenly ended the chat(an error occurred)
                        elif len(messageReceived) == 0 and self.isChatRequested == 1 \
                                and len(self.serverChattingClients) == 0:
                            self.isChatRequested = 0
                            inputs.clear()
                            inputs.append(self.tcpServerSocket)
                            print(Fore.RED + "User you're chatting with ended the chat")
                            print("Press enter to quit the chat: " + Fore.LIGHTBLACK_EX)
                        else:
                            inputs.remove(s)

            except OSError:
                pass
            except ValueError:
                pass

    def timerFunction(self):
        if not self.isChatRequested:
            self.counter = 0
            return
        self.counter += 1
        timer = threading.Timer(1, self.timerFunction)
        timer.start()
