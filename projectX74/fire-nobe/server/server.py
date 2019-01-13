# system imports
from struct import *
import socket
from socket import *
import fcntl
import os

# local system (pygame) imports
import pygame

# app imports
from messages import ClientMessages, ServerMessages, Message


# Client is a local representation of client info
class Client:
    def __init__(self, addr, handle):
	self.addr = addr
	self.handle = handle
	self.msg_queue = []
	self.defunct = 0

    def enqueue_message(self, msg):
	self.msg_queue.append(msg)


class HandleWrangler:
    "Manages handles, which are client IDs. Not thread-safe."
    def __init__(self):
	self.num_out = 0
	self.taken = { }

    # this is horribly inefficient for large numbers of clients
    def new_handle(self):
	if self.num_out > 32:
	    return -1
	handle = 1
	found = 0
	while found == 0:
	    if not self.taken.has_key(handle):
		found = 1
		self.num_out = self.num_out + 1
		self.taken[handle] = 0 # just stick something in there
	    else:
		handle = handle + 1
	return handle

    def release_handle(self, handle):
	if not self.taken.has_key(handle):
	    return
	del self.taken[handle]


class ClientWrangler:
    clients = { }

    def __init__(self):
	self.hndl_mstr = HandleWrangler()

    def new_client(self, addr):
	if self.clients.has_key(addr):
	    print "Duplicate client '", addr, "'!"
	    return None
	
	handle = self.hndl_mstr.new_handle()
	if handle < 0:
	    print "ERROR: no handle available"
	    return None

	newclient = Client(addr, handle)
	self.clients[addr] = newclient

	return newclient

    def kill_client(self, addr):
	if not self.clients.has_key(addr):
	    return
	self.hndl_mstr.release_handle(self.clients[addr].handle)
	del self.clients[addr]

    def client_exists(self, addr):
	return self.clients.has_key(addr)


class NetWrangler:
    def __init__(self):
	self.clients = {}
	self.global_fmgs = ""
	self.global_args = []

    def startup(self):
	try:
	    self.i_skt = socket(AF_INET, SOCK_DGRAM)
	    #ifcntl.fcntl(self.i_skt.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
	    self.i_skt.setblocking(0)
	    self.i_skt.bind(('', 9000))
	except error:
	    print "Error starting UDP server: '", error, "'"
	    return 0
	return 1

    def destroy(self):
	for client in self.clients:
	    client.o_skt.close()
	self.i_skt.close()
    
    # brings a new client into the system
    def new_client(self, client):
	client.o_skt = socket(AF_INET, SOCK_DGRAM)
	client.o_skt.connect((client.addr[0], 9001))

    def kill_client(self, client):
	client.o_skt.close()

    def fetch_client_messages(self):
	# maybe put this in a loop, but the caller is already in a tight
	# loop so it "shouldn't be necessary" (Famous Last Words(TM))
	try: # fetch some data out of the socket
	    data, addr = self.i_skt.recvfrom(ClientMessages.MAX_MESSAGE_SIZE)
	except error: # also handles the "no data available" case
	    return []
	
	#
	# DO NOT MUNGE THIS CODE UNLESS YOU UNDERSTAND pack/unpack WELL!
	# Either take it on faith, or read the pack/unpack docs carefully,
	# cause there be voodoo here.
	#
	msg_fmts = ClientMessages.message_formats # record these to save typing
	msg_fields = ClientMessages.message_fields
	dlen = len(data)
	messages = []
        while dlen > 0:
	    # fetch msg_type and check for correctness
	    fmt = "!B" + str(dlen - 1) + "s" # 1 byte
	    msg_type, data = unpack(fmt, data)
	    if not msg_fmts.has_key(msg_type): # SOMEONE SET UP US THE BOMB
		print "warning: received invalid message type ", msg_type
		break

	    # fetch struct fmt and check that enough data is available
	    fmt = "!" + msg_fmts[msg_type]
	    sz = calcsize(fmt)
	    dlen = len(data)

	    new_msg = Message()
	    setattr(new_msg, "type", msg_type)
	    setattr(new_msg, "addr", addr)

	    if len(fmt) > 0:
		if sz > dlen:
		    print "warning: truncated message"
		    break

		# unpack data
		fmt = fmt + str(dlen - sz) + "s"
		fields = unpack(fmt, data)
		flen = len(fields)
		data = fields[flen - 1]

		# iterate over resulting fields, adding them to the Message inst
		for i in range(0, (flen - 1)):
		    setattr(new_msg, msg_fields[msg_type][i], fields[i])

	    # reset dlen for next iteration
	    dlen = len(data)

	    messages.append(new_msg)
	# end while loop
	return messages


    def flush_client_queue(self, client):
        num_msgs = len(client.msg_queue)
	if num_msgs < 1 and len(self.global_args) < 1:
	    return

	# first, build up a string to transmit
        fmt = "!" # fmt will be a big old format for the entire xmission
	args = [] # args will be the list of args corresponding to fmt
	for msg in client.msg_queue:
	    # we will assume that this block is unnecessary since server
	    # should be smart enough to not enqueue a bogus message
	    # if not ServerMessages.message_formats.has_key(msg.type):
	    # 	print "ERROR: unsupported message to client"
	    # 	continue
	    fmt = fmt + "B" + ServerMessages.message_formats[msg.type]
	    args.append(msg.type)
	    for argname in ServerMessages.message_fields[msg.type]:
		args.append(getattr(msg, argname))
	fmt = fmt + self.global_fmt
	args.extend(self.global_args)
	xmit = pack(fmt, *args)
	client.msg_queue = []

	# xmit contains the data to be transmitted; send it
	try:
	    client.o_skt.send(xmit)
	except error:
	    client.defunct = 1

    def clear_global_queue(self):
	self.global_fmt = ""
	self.global_args = []

    def enqueue_global_message(self, msg):
	# we again assume no bogus messages get enqueued
	self.global_fmt = self.global_fmt + "B" + ServerMessages.message_formats[msg.type]
	self.global_args.append(msg.type)
	for argname in ServerMessages.message_fields[msg.type]:
	    self.global_args.append(getattr(msg, argname))


class Dispatcher:
    def __init__(self):
	pass

    def handleHELLO(self, msg):
	global cmaster
	global nmaster
	newclient = cmaster.new_client(msg.addr)
	if newclient == None:
	    print "WARNING: failed creating new client"
	    return
	newclient.addr = msg.addr
	nmaster.new_client(newclient)
	hmsg = Message()
	hmsg.type = ServerMessages.ACK_HELLO
	hmsg.handle = newclient.handle
	newclient.enqueue_message(hmsg)
	print "New client ", newclient

    def handleGOODBYE(self, msg):
        global cmaster
	global nmaster
	if not cmaster.clients.has_key(msg.addr):
	    print "ERROR: some lying bastard claims to be a client ", msg.addr
	    return
	client = cmaster.clients[msg.addr]
	nmaster.kill_client(client)
	print "Whacking ", client
	cmaster.kill_client(msg.addr)

    def handleHEARTBEAT(self, msg):
	global cmaster
	if not cmaster.clients.has_key(msg.addr):
	    print "ERROR: some lying bastard claims to be a client ", msg.addr
	    return
	client = cmaster.clients[msg.addr]

	msg = Message()
	msg.handle = client.handle
	msg.type = ServerMessages.HEARTBEAT
	# This may be a case for making a global queue of msgs to ALL clients
	# (This loop is O(n), and then it adds O(n) again later for packing
	# this message for transmission to all clients. OTOH num clients should
	# be small, so for now we'll do it this way; KISS)
	for xclient in cmaster.clients:
	    if xclient != client:
		client.enqueue_message(msg)

    def handleMY_LOCATION(self, msg):
	global cmaster
	if not cmaster.clients.has_key(msg.addr):
	    print "ERROR: some lying bastard claims to be a client ", msg.addr
	    return
	client = cmaster.clients[msg.addr]
	client.x = msg.x
	client.y = msg.y
	client.heading = msg.heading

    handlers = { }
    handlers[ClientMessages.HELLO] = handleHELLO
    handlers[ClientMessages.GOODBYE] = handleGOODBYE
    handlers[ClientMessages.HEARTBEAT] = handleHEARTBEAT
    handlers[ClientMessages.MY_LOCATION] = handleMY_LOCATION


class TopLevel:
    # tunable params
    master_freq = 30 # 200 Hz == 5 milliseconds; master clock frequency
    client_freq = 1 # fraction of master freq to run the client receive loop
    xmit_subfreq = 2 # fraction of master to run the transmission loop
    # 200/1 == 200; run client_freq at 200Hz (5ms) intervals
    # 200/10 == 20; run xmit_subfreq at 20Hz (50ms) invervals

    def __init__(self):
	self.halt = 0
	self.clock = pygame.time.Clock()
	self.client_list = { }
	self.master_cntdown = self.master_freq
	self.xmit_cntdown = self.xmit_subfreq
	self.dispatcher = Dispatcher()

	global nmaster
	nmaster = NetWrangler()
	if not nmaster.startup():
	    self.halt = 1

	global cmaster
	cmaster = ClientWrangler()

    def run(self):
	global nmaster
	print "Welcome to PX74 Airlines, flight 0x2A."
	print "We hope you enjoy your flight aboard our FireNobe 2004 XL."
	while not self.halt:
	    try:
		self.clock.tick(self.master_freq)
		self.xmit_cntdown = self.xmit_cntdown - 1
		
		msgs = nmaster.fetch_client_messages()
		for msg in msgs:
		    type = msg.type
		    if not self.dispatcher.handlers.has_key(type):
			print "ERROR: client '" +msg.addr+ "' sent unknown msg"
		    else:
			self.dispatcher.handlers[type](self.dispatcher, msg)

		if self.xmit_cntdown == 0:
		    self.xmit_cntdown = self.xmit_subfreq
		    for client in cmaster.clients.values():
			pmsg = Message()
			pmsg.type = ServerMessages.CLIENT_LOCATION
			pmsg.x = client.x
			pmsg.y = client.y
			pmsg.heading = client.heading
			pmsg.handle = client.handle
			nmaster.enqueue_global_message(pmsg)
		    for client in cmaster.clients.values():
			nmaster.flush_client_queue(client)
		    nmaster.clear_global_queue()

	    except KeyboardInterrupt:
		print "Bailing out. Thank you for flying PX74 Air."
		self.halt = 1

	nmaster.destroy()


def main():
    pygame.display.init()
    tl = TopLevel()
    try:
	import psyco
	psyco.profile()
<<<<<<< server.py
    except ImportError:
	pass
=======
    except ImportError:
	print "psyco not installed, expect a performance decrease"
>>>>>>> 1.15
    tl.run()
    pygame.display.quit()

if __name__ == '__main__': main()
