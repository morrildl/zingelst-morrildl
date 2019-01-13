#!/usr/bin/python


import os, pygame
import random
import pygame.font
from pygame.locals import *
from numpy import sin, cos, pi

depth = 16
flags = 0
#flags = FULLSCREEN
filename = "nebula.png"
scoresprite = "score.png"

class A(pygame.sprite.Sprite):
    filename = "a.png"
    def __init__(self):
	pygame.sprite.Sprite.__init__(self)
	self.master = pygame.image.load(self.filename).convert()
	self.master.set_colorkey(self.master.get_at((0,0)), RLEACCEL)
	self.image = self.master
	self.rect = self.image.get_rect()
	self.domain = pygame.display.get_surface().get_rect()
	self.x_delta = 2
	self.x_pos = random.choice(range(70,730,1))
	self.y_pos = random.choice(range(70,530,1))
	self.rect.center = (self.x_pos, self.y_pos)
	self.move_rate = 2
	self.horiz_v = self.move_rate - 2 * self.move_rate * random.choice(range(0, 2, 1))
	self.vert_v = self.move_rate - 2 * self.move_rate * random.choice(range(0, 2, 1))

    def update(self):
	self.rect = self.image.get_rect()
	self.y_pos = self.y_pos + self.vert_v
	self.x_pos = self.x_pos + self.horiz_v
	self.rect.center = (self.x_pos, self.y_pos)

	if not self.domain.contains(self.rect):
	    if self.rect.left < self.domain.left or \
	       self.rect.right > self.domain.right:
		self.horiz_v = -self.horiz_v
	    if self.rect.bottom > self.domain.bottom or \
	       self.rect.top < self.domain.top:
		self.vert_v = -self.vert_v

class B(pygame.sprite.Sprite):
    filename = "b.png"
    def __init__(self):
	pygame.sprite.Sprite.__init__(self)
	self.master = pygame.image.load(self.filename).convert()
	self.master.set_colorkey(self.master.get_at((0,0)), RLEACCEL)
	self.master = pygame.transform.rotate(self.master, 270)
	self.image = self.master
	self.rect = self.image.get_rect()
	self.domain = pygame.display.get_surface().get_rect()
	self.x_pos = 400
	self.y_pos = 300
	self.heading = 0
	self.turn_rate = 10
	self.move_rate = 5
	self.firing_cnt = 10
	self.firing_rate = self.firing_cnt
	self.rect.center = (self.x_pos, self.y_pos)

    def update(self):
	keystate = pygame.key.get_pressed()
	heading_delta = (self.turn_rate * (keystate[K_LEFT] - keystate[K_RIGHT])) % 360
	self.heading = self.heading + heading_delta
	heading_rad = pi * self.heading / 180.0
	x_delta = 0
	y_delta = 0

	if keystate[K_y]:
	    fdgb = FDGB(self.x_pos, self.y_pos, B)
	    fdgbset.add(fdgb)
	    shipset.remove(self)
	if self.firing_cnt > 0:
	    self.firing_cnt = self.firing_cnt - 1
	if keystate[K_j] or keystate[K_DOWN]:
	    x_delta = -self.move_rate * cos(heading_rad)
	    y_delta = +self.move_rate * sin(heading_rad)
	if keystate[K_k] or keystate[K_UP]:
	    x_delta = x_delta + self.move_rate * cos(heading_rad)
	    y_delta = y_delta - self.move_rate * sin(heading_rad)

	if keystate[K_SPACE] and self.firing_cnt == 0:
	    bullet = C(self.heading, self.x_pos, self.y_pos)
	    shotset.add(bullet)
	    self.firing_cnt = self.firing_rate

	self.image = pygame.transform.rotate(self.master, self.heading)
	self.rect = self.image.get_rect()
	self.rect.center = (self.x_pos + x_delta, self.y_pos + y_delta)

	if self.domain.contains(self.rect):
	    self.x_pos = self.x_pos + x_delta
	    self.y_pos = self.y_pos + y_delta

	self.rect.center = (self.x_pos, self.y_pos)

class C(pygame.sprite.Sprite):
    filename = "blast.png"
    def __init__(self, heading, x_pos, y_pos):
	pygame.sprite.Sprite.__init__(self)
	self.image = pygame.image.load(self.filename).convert()
	self.image.set_colorkey(self.image.get_at((0,0)), RLEACCEL)
	self.rect = self.image.get_rect()
	self.move_rate = 10
	self.heading_rad = pi * heading / 180.0
	self.y_pos = y_pos - 70 * sin(self.heading_rad)
	self.x_pos = x_pos + 70 * cos(self.heading_rad)

    def update(self):
	self.y_pos = self.y_pos - self.move_rate * sin(self.heading_rad)
	self.x_pos = self.x_pos + self.move_rate * cos(self.heading_rad)
	self.rect.center = (self.x_pos, self.y_pos)
	if not pygame.display.get_surface().get_rect().contains(self.rect):
	    shipset.remove(self)

class FDGB(pygame.sprite.Sprite):
    filename_base = "-fdgb.png"
    def __init__(self, x_pos, y_pos, origclass):
	pygame.sprite.Sprite.__init__(self)
	self.images = { }
	for i in range(0, 5):
	    self.images[i] = pygame.image.load(str(i)+self.filename_base).convert()
	    self.images[i].set_colorkey(self.images[i].get_at((0,0)), RLEACCEL)
	self.image = self.images[0]
	self.rect = self.image.get_rect()
	self.frame_cnt = 10
	self.cntdown = self.frame_cnt
	self.cur_frame = 0
	self.last_frame = 4
	self.x_pos = x_pos
	self.y_pos = y_pos
	self.rect.center = (x_pos, y_pos)
	self.origclass = origclass

    def update(self):
	if self.cntdown <= 0:
	    self.cur_frame = self.cur_frame + 1
	    if self.cur_frame > self.last_frame:
		shipset.add(self.origclass())
		fdgbset.remove(self)
		return
	    self.image = self.images[self.cur_frame]
	    self.rect = self.image.get_rect()
	    self.rect.center = (self.x_pos, self.y_pos)
	    self.cntdown = self.frame_cnt
	else:
	    self.cntdown = self.cntdown - 1

class Score(pygame.sprite.Sprite):
    def __init__(self):
	pygame.sprite.Sprite.__init__(self)
	self.y_pos = 8
	self.x_pos = 750
	self.font = pygame.font.Font(None, 48)
	self.font.set_italic(1)
	self.rect = Rect(self.x_pos, self.y_pos, 56, 56)

    def update(self):
	self.image = self.font.render(str(pscore), 1, (255, 255, 255))

def main():
    pygame.display.init()
    pygame.font.init()
    screen = pygame.display.set_mode((800, 600), flags, 16)
    pygame.display.set_caption("Sprite Test")
    pygame.mouse.set_visible(0)

    global pscore
    pscore = 0

    try: 
	background = pygame.image.load(filename).convert()
	score_sfc = pygame.image.load(scoresprite).convert()
	score_sfc.set_colorkey(score_sfc.get_at((0,0)), RLEACCEL)
    except pygame.error, message:
	print "Foobar: " + message

    clock = pygame.time.Clock()
    letter = A()
    bletter = B()
    global shipset
    shipset = pygame.sprite.RenderUpdates((letter, bletter))
    global fdgbset
    fdgbset = pygame.sprite.RenderUpdates()
    global shotset
    shotset = pygame.sprite.RenderUpdates()
    staticset = pygame.sprite.RenderUpdates()
    staticset.add(Score())
    background.blit(score_sfc, (800-171, 0))
    screen.blit(background, (0,0))
    pygame.display.update()
    blackhole = Rect(200, 115, 30, 30)

    while 1:
	pygame.event.pump()
	if pygame.key.get_pressed()[K_ESCAPE]:
	    break

	clock.tick(50)

	shipset.clear(screen, background)
	fdgbset.clear(screen, background)
	shotset.clear(screen, background)
	staticset.clear(screen, background)
	shipset.update()
	fdgbset.update()
	shotset.update()
	staticset.update()
	victims = pygame.sprite.groupcollide(shotset, shipset, 1, 1)
	for vict in victims:
	    ships = victims[vict]
	    for ship in ships:
		fdgb = FDGB(ship.x_pos, ship.y_pos, ship.__class__)
		fdgbset.add(fdgb)
		pscore = pscore + 1
	victims = pygame.sprite.groupcollide(shipset, shipset, 0, 0)
	fodder = { }
	for vict in victims:
	    ships = victims[vict]
	    whammo = 0
	    for ship in ships:
		if ship != vict and not fodder.has_key(ship):
		    whammo = 1
		    fodder[ship] = 1
		    shipset.remove(ship)
		    fdgbset.add(FDGB(ship.x_pos, ship.y_pos, ship.__class__))
		    if ship.__class__ == B: pscore = pscore - 1
	    if whammo and not fodder.has_key(vict):
		shipset.remove(vict)
		fodder[vict] = 1
		fdgbset.add(FDGB(vict.x_pos, vict.y_pos, vict.__class__))
		if ship.__class__ == B: pscore = pscore - 1
	for ship in shipset.sprites():
	    if ship.rect.colliderect(blackhole):
		shipset.remove(ship)
		fdgbset.add(FDGB(ship.x_pos, ship.y_pos, ship.__class__))
		if ship.__class__ == B: pscore = pscore - 1
		
	
	dirties = shipset.draw(screen)
	dirties.extend(shotset.draw(screen))
	dirties.extend(fdgbset.draw(screen))
	dirties.extend(staticset.draw(screen))
	pygame.display.update(dirties)
    
    pygame.display.quit()
    pygame.font.quit()

if __name__ == "__main__": main()
