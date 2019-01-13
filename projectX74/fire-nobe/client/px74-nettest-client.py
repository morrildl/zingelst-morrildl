import struct
from struct import pack
from struct import unpack
from struct import calcsize
import socket
from socket import *
import fcntl
import os
from math import fabs

import pygame
import pygame.font
from pygame.locals import *

from messages import ClientMessages, ServerMessages, Message
from sprites import PX74Sprite

try:
    import psyco
    psyco.profile()
except ImportError:
    print "psyco is not available, expect a performance decrease"

depth = 16
flags = 0
#flags = FULLSCREEN
fps = 100
xmit_subfreq = 4 # transmission at 100/5 = 20 Hz

class ClientNetWrangler:
    def __init__(self, remote_addr, local_addr):
	self.remote_addr = remote_addr
	self.local_addr = local_addr
	self.msg_queue = []

    def startup(self):
	try:
	    self.i_skt = socket(AF_INET, SOCK_DGRAM)
	    fcntl.fcntl(self.i_skt.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
	    self.i_skt.bind(self.local_addr)

	    self.o_skt = socket(AF_INET, SOCK_DGRAM)
	    self.o_skt.connect(self.remote_addr)
	except error:
	    print "Error creating UDP sockets: '" + net_err + "'"
	    return 0
	return 1

    def destroy(self):
	self.o_skt.close()
	self.i_skt.close()
    
    def fetch_server_messages(self):
	# maybe put this in a loop, but the caller is already in a tight
	# loop so it "shouldn't be necessary" (Famous Last Words(TM))
	try: # fetch some data out of the socket
	    data, addr = self.i_skt.recvfrom(ClientMessages.MAX_MESSAGE_SIZE)
	except error: # also handles the "no data available" case
	    return []
	if not addr[0] == self.remote_addr[0]:
	    print "WARNING: " + addr[0] + " is trying to SET UP US THE BOMB"
	    return

	#
	# DO NOT MUNGE THIS CODE UNLESS YOU UNDERSTAND pack/unpack WELL!
	# Either take it on faith, or read the pack/unpack docs carefully,
	# cause there be voodoo here.
	#
	msg_fmts = ServerMessages.message_formats # record these to save typing
	msg_fields = ServerMessages.message_fields
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

    def clear_message_queue(self):
	self.msg_queue = []

    def enqueue_message(self, msg):
	self.msg_queue.append(msg)

    def flush_message_queue(self):
        num_msgs = len(self.msg_queue)
	if num_msgs < 1:
	    return

	# first, build up a string to transmit
        fmt = "!" # this will be a big old format for the entire xmission
	args = []  # this will be the list of args corresponding to fmt
	for msg in self.msg_queue:
	    # we will assume that this block is unnecessary since server
	    # should be smart enough to not enqueue a bogus message
	    # if not ServerMessages.message_formats.has_key(msg.type):
	    # 	print "ERROR: unsupported message to client"
	    # 	continue
	    fmt = fmt + "B" + ClientMessages.message_formats[msg.type]
	    args.append(msg.type)
	    for argname in ClientMessages.message_fields[msg.type]:
		args.append(getattr(msg, argname))
	xmit = pack(fmt, *args)
	self.msg_queue = []

	# xmit contains the data to be transmitted; send it
	try:
	    self.o_skt.send(xmit)
	except error:
	    print "ERROR: transmission failed!"

class TopLevel:
    bg_filename = "nebula.png"

    def __init__(self, screen):
	self.screen = screen
	self.clock = pygame.time.Clock()
	self.shipset = pygame.sprite.RenderUpdates()

	self.halt = 0
	self.xmit_cntdown = xmit_subfreq

	self.main_sprite = PX74Sprite("b.png")
	self.shipset.add(self.main_sprite)

	# (try to) load background image
	try: 
	    self.bg_sfc = pygame.image.load(self.bg_filename).convert()
	except pygame.error, message:
	    print "Foobar: " + message
	# blit up the background image onto the screen surface
	self.screen.blit(self.bg_sfc, (0,0))
	pygame.display.update() # required after initial blit before sprites

	self.netw = ClientNetWrangler(('127.0.0.1', 9000), ('', 9001))
	if not self.netw.startup():
	    print "ERROR: couldn't start; network init failed"
	    self.halt = 1
	    return
	hellomsg = Message()
	hellomsg.type = ClientMessages.HELLO
	self.netw.enqueue_message(hellomsg)

	self.handle = 0


    def process_input(self):
	pygame.event.pump()
	keys = pygame.key.get_pressed()
	if keys[K_ESCAPE]:
	    self.netw.clear_message_queue()
	    byemsg = Message()
	    byemsg.type = ClientMessages.GOODBYE
	    self.netw.enqueue_message(byemsg)
	    self.netw.flush_message_queue()
	    self.halt = 1
	if keys[K_UP]:
	    self.main_sprite.y = self.main_sprite.y - 1
	if keys[K_DOWN]:
	    self.main_sprite.y = self.main_sprite.y + 1
	if keys[K_LEFT]:
	    self.main_sprite.x = self.main_sprite.x - 1
	if keys[K_RIGHT]:
	    self.main_sprite.x = self.main_sprite.x + 1

    def process_sprites(self):
	self.shipset.clear(self.screen, self.bg_sfc)
	self.shipset.update()
	
	dirties = self.shipset.draw(self.screen)
	pygame.display.update(dirties)

    def run(self):
	posmsg = Message()
	posmsg.type = ClientMessages.MY_LOCATION
	while not self.halt:
	    self.clock.tick(fps)
	    msglist = self.netw.fetch_server_messages()
	    for msg in msglist:
		self.handlers[msg.type](self, msg)
	    self.process_input()
	    self.process_sprites()
	    if self.xmit_cntdown == 0:
		posmsg.x = self.main_sprite.x
		posmsg.y = self.main_sprite.y
		posmsg.heading = 0
		posmsg.handle = self.handle
		self.netw.enqueue_message(posmsg)
		self.netw.flush_message_queue()
		self.xmit_cntdown = xmit_subfreq
	    else:
		self.xmit_cntdown = self.xmit_cntdown - 1
	self.netw.destroy()

    def handleHEARTBEAT(self, msg):
	print "HEARTBEAT received, ", msg.handle

    def handleACK_HELLO(self, msg):
	print "hello ACKed, ", msg.handle
	self.handle = msg.handle

    def handleCLIENT_LOCATION(self, msg):
	if self.handle < 1:
	    return
	if msg.handle == self.handle:
	    if fabs(msg.x - self.main_sprite.x) > 6 or \
	       fabs(msg.y - self.main_sprite.y) > 6:
		print "Resyncing: ", (msg.x - self.main_sprite.x), ", ", (msg.y - self.main_sprite.y)
		self.main_sprite.x = msg.x
		self.main_sprite.y = msg.y
		self.main_sprite.heading = msg.heading

    def handleSECTOR_SPRITE_DEF(self, msg):
	print "SECTOR_SPRITE_DEF received"

    handlers = {}
    handlers[ServerMessages.HEARTBEAT] = handleHEARTBEAT
    handlers[ServerMessages.ACK_HELLO] = handleACK_HELLO
    handlers[ServerMessages.CLIENT_LOCATION] = handleCLIENT_LOCATION 
    handlers[ServerMessages.SECTOR_SPRITE_DEF] = handleSECTOR_SPRITE_DEF 

def init_pygame():
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_caption("Network Test")
    screen = pygame.display.set_mode((800, 600), flags, 16)
    pygame.mouse.set_visible(0)

    return screen
    
def shutdown_pygame():
    pygame.display.quit()
    pygame.font.quit()

def main():
    screen = init_pygame()
    TopLevel(screen).run()
    shutdown_pygame()
if __name__ == "__main__": main()
