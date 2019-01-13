
import wx

class Ouidjit:
    EVT_DISCARD = 1

    def __init__(self, parent, name=None, peer=None,
		 rect=None, coords=(100,100), size=(2,2),
		 color='RED', border_width=1):
	self.parent = parent
	self.peer = peer
	self.name = name
	self.visible_to = []
	self.color = color
	self.border_width = border_width
	self.lifted = False
	if rect:
	    self.rect = rect
	    t = rect.Get()
	    self.coords = t[0:1]
	    self.size = t[2:3]
	else:
	    self.coords = coords
	    self.size = size
	    self.rect = wx.Rect(coords[0], coords[1],
				size[0], size[1])

    def __str__(self):
	fmt = "Ouidjit: %s\n\tcolor: %s\n\tborder: %s\n\tcoords: %s\n\tsize: %s\n\tlifted: %s\n\t"
	if self.name: name = self.name
	else: name = "Nameless"
	return fmt % (name, self.color, self.border_width, self.coords,
		      self.size, self.lifted)

    def render(self, dc, xy=None):
	if not dc: return

	if not xy: xy = self.coords
	x, y = xy

	dc.SetPen(wx.Pen(self.color, self.border_width))
	dc.DrawRectangle(x, y, self.size[0], self.size[1])
	if self.name: dc.DrawText(self.name, x, y + self.size[1]/2)

    def ghost_render(self, dc, xy):
	"""
	Used for alternate "ghost" renderings, e.g. for during drags.
	"""
	self.render(dc, xy=xy)

    def lift(self): self.lifted = True

    def drop(self, coords):
	self.lifted = False
	self.relocate(coords)

    def resize(self, size):
	self.size = size
	self.rect = wx.Rect(self.coords[0], self.coords[1],
			    self.size[0], self.size[1])

    def delete(self, ev):
	self.parent.remove_ouidjit(self)

    def relocate(self, xy):
	self.coords = xy
	self.rect = wx.Rect(xy[0], xy[1], self.size[0], self.size[1])

    def get_context_menu(self):
	m = wx.Menu()
	wx.EVT_MENU(self.parent, self.EVT_DISCARD, self.delete)
	m.Append(self.EVT_DISCARD, "Discard")
	return m
