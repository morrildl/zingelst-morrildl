import socket
import pygame
from pygame.locals import *
from struct import *
from socket import *
import fcntl, os

class TestClient:
    def __init__(self):
	pass

    def main(self):
	HOST = '127.0.0.1'
	PORT = 9000
	pygame.display.init()
	screen = pygame.display.set_mode((100,100), 0, 8)
	s = socket(AF_INET, SOCK_DGRAM)
	s.connect((HOST, PORT))
	isk = socket(AF_INET, SOCK_DGRAM)
	fcntl.fcntl(isk.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
	isk.bind(('',9001))
	clock = pygame.time.Clock()
	hitcnt = 0
	cnt = 0
	msg = ''
	while 1:
	    pygame.event.pump()
	    clock.tick(30)
	    keystate = pygame.key.get_pressed()
	    if keystate[K_SPACE] and hitcnt < 255:
		hitcnt = hitcnt + 1
		msg = msg + pack("!B", 3)
	    if keystate[K_h] and hitcnt < 255:
		hitcnt = hitcnt + 1
		msg = msg + pack("!B", 1)
	    if keystate[K_g] and hitcnt < 255:
		hitcnt = hitcnt + 1
		msg = msg + pack("!B", 2)

	    if keystate[K_ESCAPE]:
		break
	    cnt = cnt + 1
	    if cnt > 29:
		if hitcnt > 0:
		    # msg = pack('!B'+str(len(msg))+'s', hitcnt, msg)
		    print 'Transmitting: ', (msg, '')
		    s.send(msg)
		cnt = 0
		msg = ''
		hitcnt = 0
	    try:
		data, addr = isk.recvfrom(4096)
		print "Data: ", data
		dlen = len(data)
		vals = unpack("!H" + str(dlen - 2) + "s", data)
		nummsg = vals[0]
		print "Received ", nummsg, " messages:"
		data = vals[1]
		for i in range(0, nummsg):
		    dlen = len(data)
		    vals = unpack("!BH"+str(dlen-3)+"s", data)
		    data = vals[2]
		    print "type ", vals[0], " from ", vals[1]
	    except error:
		pass
	s.close()

def main():
    tc = TestClient()
    tc.main()
if __name__ == '__main__': main()
