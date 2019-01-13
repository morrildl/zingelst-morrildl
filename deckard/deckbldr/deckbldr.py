
import deck
from deck import Card, Deck, DeckManager
import sys
import wx
import ouidjit
from ouidjit import Ouidjit
import copy

card_width = 100
card_height = 200
dm = DeckManager()
card_files = ["../res/cards.xml", "../res/more-cards.xml", \
	      "../res/disasters.xml", "../res/cataclysms.xml"]

class CardOuidjit(Ouidjit):
    def __init__(self, parent, name=None, peer=None,
		 coords=(100,100), size=(10,10)):
	Ouidjit.__init__(self, parent, name=name, peer=peer,
			 coords=coords, size=size)
	
	if peer.image_file:
	    i = wx.Image(peer.image_file)
	    i.LoadFile(peer.image_file)
	    self.img = i.ConvertToBitmap()

	    # this was WAY fucking harder than it needed to be.  You should
	    # be able to jump straight to a Bitmap from a string, rather than
	    # have to create an Image from the string and convert the image
	    # to the Bitmap.  There is a method for this (BitmapFromBits) but
	    # there is absolutely no documentation whatsoever about what the
	    # format of that string should be, and there is no way to get
	    # access to the internal data of a Bitmap in order to figure it out.
	    # So, we have no choice but to go through an EmptyImage first.

	    # create a Bitmap containing a black/white checkerboard, to use as
	    # a mask to create a transparency/ghost effect
	    j = wx.EmptyImage(75, 100)
	    j.SetData("".join([["\x00", "\xff"][x%2]*3 for x in range(7500)]))
	    gbm = j.ConvertToBitmap()
	    self.ghost_img = i.ConvertToBitmap()
	    self.ghost_img.SetMask(wx.Mask(gbm, wx.BLACK))
	else:
	    self.img = None
	    self.ghost_img = None

    def render(self, dc, xy=None):
	x, y = self.coords
	if self.img:
	    dc.DrawBitmap(self.img, x, y, True)
	else:
	    Ouidjit.render(self, dc, xy)
	
    def ghost_render(self, dc, xy):
	x, y = xy
	if self.ghost_img:
	    dc.DrawBitmap(self.ghost_img, x, y, True)
	else:
	    tmp = self.color
	    self.color = 'BLACK'
	    Ouidjit.ghost_render(self, dc, xy)
	    self.color = tmp

class Table(wx.ScrolledWindow):
    STATE_IDLE = 1
    STATE_DRAGGING = 2

    def __init__(self, parent):
	wx.ScrolledWindow.__init__(self, parent)
	self.ouidjits = {}
	self.decks = []
	wx.EVT_PAINT(self, self.on_paint)
	self.state = self.STATE_IDLE
	self.selected = None

    def on_paint(self, ev):
	self.render(wx.PaintDC(self))

    def repaint(self, ev=None):
	self.render(wx.ClientDC(self), ev)

    def render(self, dc, ev=None):
	self.PrepareDC(dc)
	dc.BeginDrawing()

	dc.SetBackground(wx.Brush(wx.Colour(255, 255, 255)))
	dc.Clear()

	for o in self.ouidjits:
	    o.render(dc)
	
	if ev and self.state == self.STATE_DRAGGING:
	    for c in self.selected:
		xy = ev.GetX(), ev.GetY()
		c.ghost_render(dc, xy)

	dc.EndDrawing()

    def add_ouidjit(self, o):
	self.ouidjits[o] = o
	self.repaint()

    def remove_ouidjit(self, o):
	del self.ouidjits[o]
	self.repaint()

    def on_lmb_down(self, ev):
	c = self.ouidjit_at((ev.GetX(), ev.GetY()))
	if c:
	    c.lift()
	    self.state = self.STATE_DRAGGING
	    self.selected = (c,)

    def on_lmb_up(self, ev):
	xy = ev.GetX(), ev.GetY()
	if self.state == self.STATE_DRAGGING:
	    for c in self.selected:
		c.drop(xy)
		self.selected = None
		self.state = self.STATE_IDLE
		self.repaint(ev)

    def ouidjit_at(self, xy):
	for o in self.ouidjits:
	    if o.rect.Inside(xy):
		return o
	return None
	
    def on_rmb_down(self, ev):
	c = self.ouidjit_at((ev.GetX(), ev.GetY()))
	if c:
	    m = c.get_context_menu()
	    if m: self.PopupMenu(m)
	    m.Destroy()
	else:
	    # put default RMB menu here
	    pass

    def on_rmb_up(self, ev): pass

    def on_mouse_move(self, ev):
	if self.state == self.STATE_DRAGGING:
	    self.repaint(ev)
	

class TableFrame(wx.Frame):
    def __init__(self, parent, id, title, pos=wx.DefaultPosition, \
		 size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE):
	wx.Frame.__init__(self, parent, id, title, pos, size, style)

	self.table = Table(self)
	self.cards = []
	menu = wx.MenuBar()
	fileMenu = wx.Menu()
	fileMenu.Append(1, "Exit")
	menu.Append(fileMenu, "File")

	for f in card_files:
	    dm.loadXML(f)

	for i in range(2):
	    self.cards.append(None)

	i = 2
	cardMenu = wx.Menu()
	for card in dm.cards.values():
	    cardMenu.Append(i, card.title)
	    self.cards.append(card)
	    wx.EVT_MENU(self, i, self.add_card)
	    i = i + 1
	menu.Append(cardMenu, "Cards")

	deckMenu = wx.Menu()
	for deck in dm.decks.values():
	    deckMenu.Append(i, deck.name)
	    i = i + 1
	    self.cards.append(card)
	    wx.EVT_MENU(self, i, self.add_deck)
	menu.Append(deckMenu, "Decks")

	i = i + 1
	foo_menu = wx.Menu()
	foo_menu.Append(i, "Snog")
	wx.EVT_MENU(self, i, self.add_ouidjit)
	menu.Append(foo_menu, "Snog")
	
	self.SetMenuBar(menu)
	wx.EVT_MENU(self, 1, self.quit)
	wx.EVT_CLOSE(self, self.quit)


	self.SetBackgroundColour(wx.Colour(255, 255, 255))
	self.Refresh()

	wx.EVT_LEFT_DOWN(self.table, self.table.on_lmb_down)
	wx.EVT_LEFT_UP(self.table, self.table.on_lmb_up)
	wx.EVT_RIGHT_DOWN(self.table, self.table.on_rmb_down)
	wx.EVT_RIGHT_UP(self.table, self.table.on_rmb_up)
	wx.EVT_MOTION(self.table, self.table.on_mouse_move)
    
    def quit(self, ev):
	self.Destroy()

    def add_card(self, ev):
	c = self.cards[ev.GetId()]
	co = CardOuidjit(self.table, name=c.title, peer=c, size=(75,100))
	self.table.add_ouidjit(co)

    def add_deck(self, ev): pass

    def add_ouidjit(self, ev):
	o = Ouidjit(self.table, size=(100,100))
	self.table.add_ouidjit(o)

class dandeck(wx.App):
    def OnInit(self):
	self.table = TableFrame(None, 42, "Dan Deck", size=(800,600), \
		     style=wx.DEFAULT_FRAME_STYLE)
	self.table.Show()
	self.SetTopWindow(self.table)
	return True

if __name__ == '__main__':
    for arg in sys.argv[1:]:
	dm.loadXML(arg)

    app = dandeck()
    app.MainLoop()
