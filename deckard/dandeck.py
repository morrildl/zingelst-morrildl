
import deck
from deck import Card, Deck
import sys
import wx

card_width = 100
card_height = 200
dm = DeckManager()
card_files = ["res/cards.xml", "res/more-cards.xml", \
	      "res/disasters.xml", "res/cataclysms.xml"]

class Widget:
    def __init__(self, coords, width, height):
	self.coords = coords
	self.width = width
	self.height = height

    def draw(self, ctx):
	pass

    def contains(self, coords):
	if self.coords[0] <= coords[0] and \
	   self.coords[0] + self.width >= coords[0]:
	    if self.coords[1] <= coords[1] and \
	       self.coords[1] + self.width >= coords[1]:
		return True

class CardWidget(Widget):
    def __init__(self, coords, width, height, image_file, back_image_file):
	Widget.__init__(self, coords, width, height)
	self.face_up = True
	img = wx.Image(image_file, wx.BITMAP_TYPE_PNG)
	self.image = wx.Bitmap(img.rescale(card_width, card_height), -1)
	img = wx.Image(back_image_file, wx.BITMAP_TYPE_PNG)
	self.back_image = wx.Bitmap(img.rescale(card_width, card_height), -1)

    def flip(self):
	self.face_up = not self.face_up

    def draw(self, ctx):
	ctx.setPen(wx.Pen('BLACK', 2))
	ctx.drawRectangle((self.coords[0]-2, self.coords[1]-2), \
			  (self.width + 4, self.height + 4))
	if self.face_up:
	    ctx.drawBitmap(self.image, coords, False)
	else:
	    ctx.drawBitmap(self.back_image, coords, False)

class Table(wx.ScrolledWindow):
    def __init__(self):
	wx.ScrolledWindow.__init__(self)
	self.cards = []
	self.decks = []

    def Draw(self, dc):
	pass

class TableFrame(wx.Frame):
    def __init__(self, parent, id, title, pos=wx.DefaultPosition, \
		 size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE):
	wx.Frame.__init__(self, parent, id, title, pos, size, style)

	self.table = Table(self)
	menu = wx.MenuBar()
	fileMenu = wx.Menu()
	fileMenu.append(1, "Exit")
	menu.append(fileMenu, "File")

	for f in card_files:
	    dm.loadXML(f)

	i = 2
	cardMenu = wx.MenuBar()
	for card in dm.cards:
	    cardMenu.append(card.title, card.title)
	    i = i + 1
	menu.append(cardMenu, "Cards")

	deckMenu = wx.MenuBar()
	for deck in dm.decks:
	    deckMenu.append(deck.title, deck.title)
	    i = i + 1
	menu.append(deckMenu, "Cards")

	self.setMenuBar(menu)
	wx.EVT_MENU(self, 1, self.quit)
    
class dandeck(wx.App):
    def OnInit(self):
	self.table = TableFrame(None, -1, 42, "Dan Deck", size=(800,600), \
		     style=wx.DEFAULT_FRAME_STYLE)
	self.table.Show()
	self.SetTopWindow(self.table)
	return True
