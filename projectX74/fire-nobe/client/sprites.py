import pygame
from pygame.locals import *

class PX74Sprite(pygame.sprite.Sprite):
    def __init__(self, img_filename):
	pygame.sprite.Sprite.__init__(self)
	self.master = pygame.image.load(img_filename).convert()
	self.master.set_colorkey(self.master.get_at((0,0)), RLEACCEL)
	self.image = self.master
	self.rect = self.image.get_rect()
	self.domain = pygame.display.get_surface().get_rect()
	self.x_delta = 2
	self.x = 400
	self.y = 300
	self.rect.center = (self.x, self.y)
	self.move_rate = 2

    def update(self):
	self.rect = self.image.get_rect()
	self.rect.center = (self.x, self.y)
