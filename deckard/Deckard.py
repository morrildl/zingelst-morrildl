import wx 
import random
import sys
import math
import types

import deck
from deck import DeckManager

import decknet
from decknet import *

import threading
from threading import *

import time
from time import sleep

import pickle

#import psyco

BUFFERED = 1
DO_SPLASH = 0

# Table command list
TBL_NO_CMD	    = 0
TBL_DRAW_CARD	    = 1
TBL_DRAW_DECK	    = 2
TBL_PLACE_CARD	    = 3
TBL_DRAG_SELECT	    = 4
TBL_DRAG_OBJS	    = 5
TBL_DRAW_COUNTER    = 6
TBL_NEW_OBJECT	    = 7 

TBL_ZORDER_TOP	    = 0
TBL_ZORDER_BOTTOM   = 1
TBL_ZORDER_NEXT     = 2
TBL_ZORDER_PREV     = 3

FACE_UP		    = 1
FACE_DOWN	    = 2

CARD_NORMAL	= 1
CARD_TAPPED	= 2

# Used to protect looking through a deck.
# In debugging or non-game situations, you can list out a deck
# In a game situation, you protect the decks and no one can look through them
PROTECT_DECKS = 0 # PROTECT MY BALLS! LET'S FIGHTING LOVE!

# Net Messages
NET_MESSAGES = {
    1: MessageType('CHAT', '128s', ['text']),
    2: MessageType('PING', 'I', ['pingVal']),
    3: MessageType('HELLO', '128s', ['nick']),
    4: MessageType('ADDCARD', '256sIII',['cardname','x','y','uid']), # imposes an arbitrary limit of 256 chars to the card names, not sure if this should be replaced by an MD5 or something
    5: MessageType('MOVEOBJ', 'III', ['uid', 'x','y']),
    # objStateHash is object specific info that has to be communicated to remote clients. For cards, such things as
    # the facing and tapped state, etc.
    6: MessageType('ADDOBJ', '16s128sIII256s',['objType', 'name', 'x', 'y', 'uid', 'objStateData']),
    7: MessageType('REFLECTOBJSTATE', 'I64s256s', ['uid', 'key', 'value']),
    8: MessageType('REMOVEOBJ', 'I', ['uid']),
    9: MessageType('ADDTODECK', 'II', ['uid', 'carduid']),
    10: MessageType('REMOVEFROMDECK', 'II', ['uid', 'carduid'])
}

class UIDGen:
    """
    Generates identifiers that can be used to create objects with
    network wide names It is just an incrementer with a few rules
    attached. Everytime you make an object that has network
    visibility, call GetNextUID(). That's all for the caller. Once
    the remote client gets the uid, they must seed their UIDGen with
    the uid that was passed to them. Everyone on the network must
    keep their UIDGens in sync so that common shared objects can be
    found across clients There are better UIDs to be had, so this
    class can be updated when we come up with them
    """
    def __init__(self, id):
	self.UID = id
	self.count = 0

    def SetUID(self, id):
	self.UID = id

    def SeedUID(self, uid):
	"""
	Use this to set up the UIDGen for the next use
	"""
	self.count = uid
    
    def GetNextUID(self):	
	self.count = self.count + 1	
	return(self.UID*65536+self.count)

GLOBAL_UIDGen = UIDGen(1)

class BlackboardMsg:
    def __init__(self, _owner, _type, _objs):
	self.type = _type
	self.objs = _objs
	self.owner = _owner; # Originator (owner) of this message

    def getType(self):
	return self.type

    def getObjs(self):
	return self.objs

    def getOwner(self):
	return self.owner

class Blackboard:
    def __init__(self):
	self.msg = []
	self.listeners = []
	
    def find(self, _type):
	for m in self.msg:
	    if(m.getType() == _type):
		return m
	
    def addMessage(self, msg):
	self.msg.append(msg)
	for listener in self.listeners:
	    listener.NotifyBB(msg)

    def removeMessage(self, msg):
	self.msg.remove(msg)

    def clearMessages(self):
	self.msg = []
	
    def addListener(self, listener):
	self.listeners.append(listener)
	
    def removeListener(self, listener):
	self.listeners.remove(listener)
	
GLOBAL_Blackboard = Blackboard()
BBM_DRAGOBJS	= 1
BBM_DRAGACCEPT	= 2

class AskDialog(wx.Dialog):
    def __init__(self, parent, id, title, pos = wx.DefaultPosition, size=wx.DefaultSize, style=wx.DEFAULT_DIALOG_STYLE, name="dlg"):
	wx.Dialog.__init__(self, parent, id, title, pos, size, style, name)

	sizer = wx.BoxSizer(wx.VERTICAL)
	self.edit = wx.TextCtrl(self, -1)

	horiz = wx.BoxSizer(wx.HORIZONTAL)
	self.okBtn = wx.Button(self, -1, "OK")
	self.cancelBtn = wx.Button(self, -1, "Cancel")
	horiz.Add(self.okBtn)
	horiz.Add(self.cancelBtn)

	sizer.Add(self.edit)
	sizer.Add(horiz)
	
	self.okBtn.SetDefault()

	# cind some events
	self.Bind(wx.EVT_BUTTON, self.OK, self.okBtn)
	self.Bind(wx.EVT_BUTTON, self.Cancel, self.cancelBtn)

	sizer.RecalcSizes()
	sizer.Fit(self)

	self.result = None

    def OK(self, event):
	self.result = self.edit.GetValue()
	self.EndModal(1)
	
    def Cancel(self, event):
	self.EndModal(0)

class GfxObj:
    def __init__(self, type, x, y, height, width, parent, peer=None, uid=0):
	#self.x = x
	#self.y = y
	#self.width = height
	#self.height = width
	self.rect = wx.Rect(x,y, height, width)
	self.type = type
	self.inSelect = 0
	self.parent = parent
	self.peer = peer
	self.uid = uid
	self.owner = None # This will eventually be used in a networked environment
			  # to make sure people aren't sneaking peeks at other 
			  # people's cards
			  
	self.uid = uid
	
    def Move(self, x, y):
	self.rect.SetX(x)
	self.rect.SetY(y)

    def Offset(self, dx, dy):
	self.rect.Offset((dx,dy))

    def SetHighlighted(self, val):
	self.inSelect = val

    def Intersect(self, x, y):
	return self.rect.Inside((x,y)) 

    def Within(self, ul, lr):
	width = math.fabs(ul[0] - lr[0])
	height = math.fabs(ul[1] - lr[1])
	selection = wx.Rect(ul[0], ul[1], width, height)
	return selection.Intersects(self.rect)

    def GetX(self):
	return(self.rect.GetX())

    def GetY(self):
	return(self.rect.GetY())
    
    def SetX(self,x):
	self.rect.x = x
	
    def SetY(self,y):
	self.rect.y = y

    # Returns a tuple containing the (x,y) coordinate of the object
    def GetXY(self):
	return((self.rect.x, self.rect.y))

    def GetPopupMenu(self):
	return (None, {})
   
    def DoPopupMenu(self, selection):
	pass
   
    def HandleEvent(self, event):
	return(False)

    def DropObjs(self, objList):
	return([])
    
    def Draw(self, dc):
	pass

    def GetStateData(self):
	"""
	This returns a hashtable of transient object state that a remote 
	client needs to replicate the object accurately
	"""
	return(dict())

class Deck(GfxObj):
    def __init__(self, name, x, y, parent, _uid=0):
	GfxObj.__init__(self, "deck", x, y, 50, 75, parent, uid=_uid)
	self.name = name
	self.cards = []
	self.facing = FACE_UP

    def Shuffle(self):	    
	pass

    def SetFacing(self, face):
	self.facing = face
	GLOBAL_NetManager.Reflect(self, "facing", self.facing)

    def FlipDeck(self):
	if(self.facing == FACE_UP):
	    self.facing = FACE_DOWN
	else:
	    self.facing = FACE_UP
   	GLOBAL_NetManager.Reflect(self, "facing", self.facing)
	# Apply the deck option to all the cards in the deck
	for card in self.cards:
	    card.SetFacing(self.facing)
	    GLOBAL_NetManager.Reflect(card, "facing", self.facing)

    def Draw(self, dc):
	# dc should already be draw-able
	(x, y) = self.rect.GetTopLeft()
	width = self.rect.GetWidth()
	height = self.rect.GetHeight()
	area = (width, height)

	if self.inSelect:
	    dc.SetPen(wx.Pen('YELLOW', 2))
	    dc.DrawRectangle(x-2, y-2, width+14, height+14)

	dc.SetPen(wx.Pen('BLACK', 1))
	
	dc.DrawRectangle(x+10, y+10, width, height)
	dc.DrawRectangle(x+5, y+5, width, height)
	
	if len(self.cards) == 0:	    
 	    dc.DrawRectangle(x, y, width, height)
	    dc.DrawText("Empty", x+5, y+10)
	else:
	    if self.facing == FACE_DOWN:    
		dc.DrawRectangle(x, y, width, height)
	    else:
		self.cards[-1].Move(x,y)
		self.cards[-1].Draw(dc)
	
	dc.DrawText(self.name, x+5, y+height+10)

    def GetPopupMenu(self):
	popup = wx.Menu()
	popup.Append(10, "Draw Card")
	popup.Append(11, "Shuffle")
	popup.Append(12, "Load Deck")
	popup.Append(13, "List Deck")
	popup.Append(14, "Delete Deck")
	popup.Append(15, "Flip Deck")
	
	actionHash = { 10:(Deck.OnDrawCard,False), 11:(Deck.OnShuffle, True), 12:(Deck.OnLoadDeck, False), 13:(Deck.OnList, True), 14:(Deck.OnDelete, True), 15:(Deck.FlipDeck,True)}
	
	return (popup, actionHash)
    
    def DropObjs(self, objs):
	acceptedObjs = []
	print "Dropping Objs "+ str(len(objs))
	for o in objs:
	    if o != self: # Don't drop ourselves on ourselves
		if isinstance(o, Card):
		    if(self.facing == FACE_DOWN):
			o.FaceDown()
		    else:
			o.FaceUp()
		    # If someone drops a bunch of cards on us, add them to all the network instances of the deck	
		    if(GLOBAL_NetManager.ready):
			m = DecknetMessage()
			m.type = 9
			m.uid = self.uid
			m.carduid = o.uid

			GLOBAL_NetManager.sendMessage(m)
		    self.cards.append(o)
		    acceptedObjs.append(o)
		    print "Appending "+o.name
		else:
		    print "Only cards can be dropped for now"

	return acceptedObjs

    def HandleEvent(self, event):
	x = event.GetX() - self.GetX()
	y = event.GetY() - self.GetY()
	
	if(event.m_shiftDown):
	    print "Draw Card"
	    self.OnDrawCard()
	    return(True)

	return(False)

    # Nuke our bad selves. The cards should disappear too
    def OnDelete(self):
	self.parent.Remove(self)

    def OnList(self):
	if PROTECT_DECKS == 0:
	    for card in self.cards:
		print card.name

    def OnDrawCard(self):
	if len(self.cards) > 0:
	     card = self.cards.pop()
	     
	     if(GLOBAL_NetManager.ready):
		m = DecknetMessage()
		m.type = 10
		m.uid = self.uid
		m.carduid = card.uid
		GLOBAL_NetManager.sendMessage(m)
		
	self.parent.SetDropObj(card)
	
    def OnShuffle(self):
	random.shuffle(self.cards)
	random.shuffle(self.cards)
	random.shuffle(self.cards)

    def AddCard(self, card):
	card.SetFacing(self.facing)
	self.cards.append(card)

    def OnLoadDeck(self):
	print "Pop3"

class Marker(GfxObj):
    def __init__(self, name, x, y, parent, _uid=0):
	GfxObj.__init__(self, "marker", x, y, 20, 20, parent, uid=_uid)
	self.color =wx.Colour(0,0,0) # Black marker by default
	self.name = name

    def GetPopupMenu(self):
	popup = wx.Menu()
	popup.Append(10, "Set Color")
	popupHash = {10:(Marker.SetColor, False)}
	return (popup,popupHash)

    def SetColor(self):
	dlg = wx.ColourDialog(self.parent)
	if(dlg.ShowModal() == wx.ID_OK):
	    self.color = dlg.GetColourData().GetColour()

    def Draw(self, dc):
	(x, y) = self.rect.GetTopLeft()
	width = self.rect.GetWidth()
	height = self.rect.GetHeight()
	area = (width, height)

	if self.inSelect:
	    dc.SetPen(wx.Pen('YELLOW', 2))
	    dc.DrawRectangle(x-2, y-2, width+2, height+2)

	dc.SetPen(wx.Pen(self.color, 1))
	dc.SetBrush(wx.Brush(self.color))
        dc.DrawCircle(x+10, y+10, 10)
	dc.SetBrush(wx.NullBrush)
	dc.SetPen(wx.NullPen)

    def HandleNetMessage(self, m):
	if(m.key == 'SetColor'):
	    self.color = m.value

class Counter(GfxObj):
    def __init__(self, name, x, y, parent, _uid=0):
	GfxObj.__init__(self, "counter", x, y, 60, 30, parent, uid=_uid)
	self.name = name
	self.count = 0

    def HandleEvent(self, event):
	x = event.GetX() - self.GetX()
	y = event.GetY() - self.GetY()
	retVal = False
	if event.LeftDown():
	    print "X:",x," y:", y
	    if x<25:
		self.count = self.count - 1	    
		retVal = True
	    elif x>45:
		self.count = self.count +1
		retVal = True
	    
	    if(retVal == True):
		GLOBAL_NetManager.Reflect(self, "count", self.count)
	
	return(retVal)
	
    def Draw(self, dc):
	(x, y) = self.rect.GetTopLeft()
	width = self.rect.GetWidth()
	height = self.rect.GetHeight()
	area = (width, height)

	if self.inSelect:
	    dc.SetPen(wx.Pen('YELLOW', 2))
	    dc.DrawRectangle(x-2, y-2, width+14, height+14)

	dc.SetPen(wx.Pen('BLACK', 1))
        dc.DrawRectangle(x, y, width, height)
	dc.DrawRectangle(x+15, y, 30, height)
	dc.DrawLine(x+12,y+5,x+3,y+15)
	dc.DrawLine(x+3,y+15,x+12,y+25)
	
	dc.DrawLine(x+48,y+5,x+57,y+15)
	dc.DrawLine(x+57,y+15,x+48,y+25)
	
	dc.DrawText(str(self.count), x+18, y+9)

    def GetPopupMenu(self):
	popup = wx.Menu()
	popup.Append(10, "Set Counter")
	popup.Append(11, "Reset Counter")
	popupHash = {10:(Counter.SetCounter, False), 11:(Counter.ResetCounter, True)}
	return (popup, popupHash)

    def ResetCounter(self):
	self.count = 0
	GLOBAL_NetManager.Reflect(self, "count", self.count)

    def SetCounter(self):
	dlg = AskDialog(None, -1, "Set Count")
	if(dlg.ShowModal()):
	    self.count = int(dlg.result)
	    GLOBAL_NetManager.Reflect(self, "count", self.count)

class RNG(GfxObj):
    def __init__(self, name, x, y, parent, peer=None, _uid=0):
	GfxObj.__init__(self, "rng", x, y, 50, 50, parent, peer, _uid)
	self.name = name
	self.parent = parent
	self.radix = 6
	self.rollCount = 1
	self.roll = 0

    def HandleEvent(self, event):
	if(event.LeftDown()):
	    x = event.GetX() - self.GetX()
	    y = event.GetY() - self.GetY()
	    print "X:",x," y:", y

	    if y > 20:
		self.roll = 0
		for i in range(0, self.rollCount):
		    self.roll = self.roll + random.randint(1, self.radix)
		GLOBAL_NetManager.Reflect(self, "roll", self.roll)

	return(False)
    
    def GetPopupMenu(self):
	popup = wx.Menu()
	popup.Append(10, "Set Die")
	popup.Append(11, "Set Roll Count")
	popupHash = {10:(RNG.SetDie, False), 11:(RNG.SetRollCount, False)}
	return (popup, popupHash)
 
    def SetDie(self):
	dlg = AskDialog(None, -1, "Set Die")
	if(dlg.ShowModal()):
	    self.radix = int(dlg.result)
	    GLOBAL_NetManager.Reflect(self, "radix", self.radix)
	
    def SetRollCount(self):
	dlg = AskDialog(None, -1, "Set Roll Count")
	if(dlg.ShowModal()):
	    self.rollCount = int(dlg.result)
	    GLOBAL_NetManager.Reflect(self, "rollCount", self.rollCount)
	    
 
    def Draw(self, dc):
	(x, y) = self.rect.GetTopLeft()
	width = self.rect.GetWidth()
	height = self.rect.GetHeight()
	area = (width, height)

	if self.inSelect:
	    dc.SetPen(wx.Pen('YELLOW', 2))
	    dc.DrawRectangle(x-2, y-2, width+4, height+4)

	dc.SetPen(wx.Pen('BLACK', 1))
        dc.DrawRectangle(x, y, width, height)
	txt = "%dd%d" % (self.rollCount, self.radix)
	dc.DrawText(txt, self.GetX()+3, self.GetY()+3)
	if(self.roll != 0):
	    dc.DrawText(str(self.roll), self.GetX()+8, self.GetY()+33)
	

class ActionMenu(wx.EvtHandler):
    def __init__(self, window, pos, clickedObj, objList):
	wx.EvtHandler.__init__(self)
	self.objList = []
	self.origObj = clickedObj
	
	# Only apply the actions to the type of objects in the selection that
	# match the original clicked on item
	for item in objList:
	    if isinstance(item, clickedObj.__class__):
		self.objList.append(item)

	if(len(self.objList) == 0):
	    self.objList.append(clickedObj)

	(menu, self.actionHash) = clickedObj.GetPopupMenu()
	if menu != None:
	    for id in self.actionHash.keys():
		wx.EVT_MENU(self, id, self.DoActions)

	    window.PushEventHandler(self)
	    window.PopupMenu(menu, pos)
	
	    menu.Destroy()
	    window.PopEventHandler()

    def DoActions(self, event):
	id = event.GetId()
	(func, multiOK) = self.actionHash[id]
	# If the function supports multiple objects, map the function to the list,
	# if the function can't support multiple objects, only operate on the original clicked object
	if multiOK == True:
	    map(func, self.objList)
	else:
	    func(self.origObj)
	
class Card(GfxObj):
    def __init__(self, name, x, y, parent, peer=None, uid=0, stateData=None):
	GfxObj.__init__(self, "card", x, y, 50, 75, parent, peer, uid)
	self.name = name
	if stateData == None:
	    self.state = CARD_NORMAL
	    self.facing = FACE_UP
	else:
	    self.state = stateData['state']
	    self.facing = stateData['facing']
	
	if peer and peer.image_file:
	    i = wx.Image('res/'+peer.image_file)
	    i.Rescale(50,75)
	    if i.Ok():
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
		print 'Card.__init__: Bad image load'
		self.img = None
		self.ghost_img = None
	else:
	    self.img = None
	    self.ghost_img = None

    def GetStateData(self):
	return(dict({'facing':self.facing, 'state':self.state}))

    def GetPopupMenu(self):
	popupMenu = wx.Menu()
	popupMenu.Append(10, "Tap")
	popupMenu.Append(11, "Flip")
	popupMenu.Append(12, "Remove")

	# Tuple is the funcion to call, and then if the call can be mapped to multiple objects
	popupHash = {10:(Card.Tap, True), 11:(Card.Flip, True), 12:(Card.Remove,True)}
	
	return (popupMenu, popupHash)

    def DoPopupMenu(self, selection):
	optList = obj.GetPopupOptions()

    def Remove(self):
	self.parent.Remove([self])
	if(self in self.parent.curSelection):
	    self.parent.curSelection.remove(self)

    def Tap(self):
	if self.state == CARD_NORMAL:
	    self.state = CARD_TAPPED
	else:
	    self.state = CARD_NORMAL
	GLOBAL_NetManager.Reflect(self, "state", self.state)

    def Flip(self):
	if self.facing == FACE_UP:
	    self.facing = FACE_DOWN
	else:
	    self.facing = FACE_UP
	    
	GLOBAL_NetManager.Reflect(self, "facing", self.facing)
	
    def FaceDown(self):
	self.facing = FACE_DOWN
	GLOBAL_NetManager.Reflect(self, "facing", self.facing)

    def FaceUp(self):
	self.facing = FACE_UP
	GLOBAL_NetManager.Reflect(self, "facing", self.facing)

    def SetFacing(self, face):
	self.facing = face
	GLOBAL_NetManager.Reflect(self,"facing", self.facing)

    def Draw(self, dc):
	# dc should already be draw-able
	(x, y) = self.rect.GetTopLeft()
	width = self.rect.GetWidth()
	height = self.rect.GetHeight()
	area = (width, height)	
		
	if self.inSelect:
	    dc.SetPen(wx.Pen('YELLOW', 3))
	    dc.DrawRectangle(x-5, y-5, width+10, height+10)

	dc.SetPen(wx.Pen('BLUE', 4))	
	
        if self.img:
	    if self.inSelect:
		dc.DrawBitmap(self.ghost_img, x, y, True)
	    else:	
		dc.DrawBitmap(self.img, x, y, True)
	else:
	    dc.DrawRectangle(x, y, width, height)
	
	if self.state == CARD_TAPPED:
	    dc.DrawLine(x+width-10, y, x+width, y+10)   
	if self.facing == FACE_UP:
	    font = wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL)
	    dc.SetFont(font)
	    dc.DrawText(self.name, x + 5, y+height+3)

class Surface(wx.ScrolledWindow):
    def __init__(self, parent, id, width, height, size = wx.DefaultSize ):
	wx.ScrolledWindow.__init__(self, parent, id, wx.Point(0, 0), size, wx.SUNKEN_BORDER)

	self.maxWidth  = width
        self.maxHeight = height
        self.x = self.y = 0
	self.gfxObjs = [] # List of all gfx objs (basically the concat of cards, decks, counters, etc)
	self.listeners = [] # List used to keep track of who wants to be notified of Table events
			    # USed for the CardInfo window to track which card needs to be displayed
	self.moveObjs = []			    
	self.newGUIObj = None # Used to hold a temporary copy of a new GUI object that user wants to create
	self.uidHash = {} # Hash that maps UIDs to GfxObjs

	self.reqCmd = TBL_NO_CMD
	
	if BUFFERED:
	    # Initialize the buffer bitmap.  No real DC is needed at this point.
	    self.buffer = wx.EmptyBitmap(self.maxWidth, self.maxHeight)
	    dc = wx.BufferedDC(None, self.buffer)
            dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
            dc.Clear()

    def GetObj(self, x, y):
	objs = []
	# Loop through all the Objs on the table and figure out what is on top
	for o in self.gfxObjs:
	    #if(o not in self.curSelection): # Don't report anything in the current selection (It's technically off-table)
	    if o.Intersect(x,y):
		objs.append(o)
	return objs
    
    def GetObjsInRect(self, start, end):
	objs = []
	for o in self.gfxObjs:
	    if o.Within(start,end):
		objs.append(o)
	return objs

    def ConvertEventCoords(self, event):
        xView, yView = self.GetViewStart()
        xDelta, yDelta = self.GetScrollPixelsPerUnit()
        return (event.GetX() + (xView * xDelta),
                event.GetY() + (yView * yDelta))

    # The newGUIObj is a newly created GfxObj that is in limbo waiting to be dropped
    # on the table by the user.
    def SetDropObj(self, obj):
	self.newGUIObj = obj
	self.reqCmd = TBL_NEW_OBJECT
	
    # Places an object at the top or the bottom of the drawing stack
    def MoveZOrder(self, obj, direction):
	if(len(self.gfxObjs) > 0):
	    idx = self.gfxObjs.index(obj)
	    self.gfxObjs.remove(obj)
	
	if direction == TBL_ZORDER_TOP:
	    self.gfxObjs.append(obj)
	elif direction == TBL_ZORDER_BOTTOM:	    
	    self.gfxObjs.insert(0, obj)
	elif direction == TBL_ZORDER_NEXT:
	    if(idx != len(self.gfxObjs)):
		self.gfxObjs.insert(idx+1,obj)
	    else:
		self.gfxObjs.append(obj)
	elif direction == TBL_ZORDER_PREV:
	    if idx == 0:
		self.gfxObjs.insert(0, obj)
	    else:
		self.gfxObjs.insert(idx-1, obj)
		
    # Accepts both individual items and lists of items to be removed to the table
    def Remove(self, objs, reflect=True): 
	print type(objs)
	if type(objs) is types.InstanceType:
	    objs = [objs]
	for o in list(objs):
	    print o.name
	    self.gfxObjs.remove(o)
	    del self.uidHash[o.uid]

	    # Send the net message if everything is ready
	    if(GLOBAL_NetManager.ready and reflect == True):
		m = DecknetMessage()
		m.type = 8
		m.uid = o.uid

		GLOBAL_NetManager.sendMessage(m)

	self.Redraw()

    # Let's other windows get info about what's going on in the table
    def AddListener(self, listener):
	self.listeners.append(listener)

    def OnPaint(self, event):
        if BUFFERED:
            # Create a buffered paint DC.  It will create the real
            # wxPaintDC and then blit the bitmap to it when dc is
            # deleted.  Since we don't need to draw anything else
            # here that's all there is to it.
            dc = wx.BufferedPaintDC(self, self.buffer)
        else:
            dc = wx.PaintDC(self)
            self.PrepareDC(dc)
            # since we're not buffering in this case, we have to
            # paint the whole window, potentially very time consuming.
        self.DoDrawing(dc)
	
    def Redraw(self):
	cdc = wx.ClientDC(self)
	self.PrepareDC(cdc)
	dc = wx.BufferedDC(cdc, self.buffer)
	self.DoDrawing(dc)
		
class Group:
    def __init__(self, parent, id, objs):
	self.parent = parent
	self.uid = id
	self.objs = objs    
    
class Table(Surface):
    def __init__(self, parent, id, size = wx.DefaultSize):
	Surface.__init__(self, parent, id, 1000, 1000, size)
	
        self.x = self.y = 0
        self.drawing = False
	self.showGrid = True
	self.snapGrid = True
	self.gridSize = 15

	self.curCardCnt = 0 # Used to keep track of how many cards have been created (Testing)
	self.curDeckCnt = 0 # Used to keep track of how many decks have been created (Testing)

	self.dragOffset = (0,0)
	self.dragOriginXY = (0,0) # Used to figure out how far to offset objects during a drag op
	self.dragOrigins = {} # Hash used as a list to track where objects were before a drag operation
	self.placingCard = None 
	self.rbsel = [] # Used to keep track of the bounds of the current rubber band select rectangle
	self.curSelection = [] # List of currently selected items
	self.reqCmd = TBL_NO_CMD # Requested command, allows other event sinks to 
			# request that the table do things
	
	self.SetScrollbars(20, 20, self.maxWidth/20, self.maxHeight/20)	
	
	wx.EVT_LEFT_DOWN(self, self.OnLeftButtonEvent)	
	wx.EVT_LEFT_UP(self, self.OnLeftButtonEvent)
	wx.EVT_RIGHT_DOWN(self, self.OnRightButton)
	wx.EVT_RIGHT_UP(self, self.OnRightButton)
	wx.EVT_MOTION(self, self.OnMouseMove)
	wx.EVT_LEAVE_WINDOW(self, self.OnMouseLeave)
	wx.EVT_ENTER_WINDOW(self, self.OnMouseEnter)
	wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_KEY_DOWN(self, self.OnKeyDown)

    # Accepts both individual items and lists of items to be added to the table
    def AddToTable(self, objs, reflect = True):
	if type(objs) is types.InstanceType:
	    objs = [objs]
	for o in list(objs):
	    self.gfxObjs.append(o)
	    print "Adding hash-"+str(o.uid)
	    self.uidHash[o.uid] = o
	    
	     # Send the net message if everything is ready
	     # Also, if we're calling this from NetAddObj, don't reflect the add 
	     # back out to the network
	    if(GLOBAL_NetManager.ready and reflect == True):
		m = DecknetMessage()
		m.type = 6
		m.objType = str(o.type)
		m.name = str(o.name)
		m.x = o.GetX()
		m.y = o.GetY()
		m.uid = o.uid
		m.objStateData = pickle.dumps(o.GetStateData())

		GLOBAL_NetManager.sendMessage(m)
		
	self.Redraw()

    def NetAddObj(self, m, peer):
	"""
	Handles putting objects on the table from remote clients
	"""
	print "In NetAdd obj", m.objType
	m.objType = m.objType.rstrip("\x00")
	m.name = m.name.rstrip("\x00")
	obj = None
	stateData = pickle.loads(m.objStateData.rstrip("\x00"))
	print stateData
	if(m.objType == "card"):
	    print "Adding card"
	    cardData = dm.cards[m.name]
	    if(cardData != None):
		obj = Card(cardData.title, m.x, m.y, self, peer = cardData, uid=m.uid, stateData = stateData)	    
	elif(m.objType == "deck"):
	    print "Adding deck"
	    obj = Deck(m.name, m.x, m.y, self, _uid=m.uid)
	elif(m.objType == "rng"):
	    print "Adding RNG"
	    obj = RNG(m.name, m.x, m.y, self, _uid=m.uid)
	elif(m.objType == "marker"):
	    print "Add Marker"
	    obj = Marker(m.name, m.x, m.y, self, _uid=m.uid)
	elif(m.objType == "counter"):
	    print "Add counter"
	    obj = Counter(m.name, m.x, m.y, self, _uid=m.uid)
	    
	if(obj != None):
	    self.AddToTable(obj, False)
	self.Redraw()
	
    def NetAddCard(self, m, peer):
	"""
	Handles sticking a card on the table surface from a remote client
	"""
	cardData = dm.cards[m.cardname.rstrip("\x00")]
	if(cardData != None):
	    newCard = Card(cardData.title, m.x, m.y, self, peer = cardData, uid=m.uid)	    
	    self.AddToTable(newCard)
	    # Update the UID Generator
	    #GLOBAL_UIDGen.SeedUID(m.uid)
    
    def NetMoveObj(self, m, peer):
	"""
	Handles moving a card in response to a network message
	"""
	if m.uid in self.uidHash:
	    o = self.uidHash[m.uid]
	    o.Move(m.x, m.y)
	    self.Redraw()
    
    def NetObjState(self, m, peer):
	"""
	Handles setting state on objects
	"""
	print "NetObjState"
	if m.uid in self.uidHash:
	    o = self.uidHash[m.uid]
	    print o.name
	    key = m.key.rstrip("\x00")
	    value = pickle.loads(m.value.rstrip("\x00"))
	    print key,"-",value
	    setattr(o, key, value)
	    self.Redraw()
    
    def NetRemoveObj(self, m, peer):
	"""
	Handles removing an object from the table
	"""
	print "NetRemoveObj"
	if(m.uid in self.uidHash):
	    o = self.uidHash[m.uid]
	    print o.name
	    self.Remove(o, False)
	    self.Redraw()
    
    def NetAddCardToDeck(self, m, peer):
	"""
	Puts a card into a deck
	"""
	if(m.uid in self.uidHash):
	    deck = self.uidHash[m.uid]
	    card = self.uidHash[m.carduid]
	    deck.AddCard(card)
    
    def NetRemoveCardFromDeck(self, m, peer):
	"""
	Removes a card from a deck
	"""
	if(m.uid in self.uidHash):
	    deck = self.uidHash[m.uid]
	    deck.cards.pop()
    
    def OnKeyDown(self, event):
	if event.GetKeyCode() == 71:
	    if(len(self.curSelection) > 0):
		pass
		#g = new Group(self, GLOBAL_UIDGen.GetNextUID(), self.curSelection)
		#self.groups.append(g)
		
    def OnMouseMove(self, event):
	(x,y) = self.ConvertEventCoords(event)
	if self.reqCmd == TBL_NO_CMD:
	    # Tell anyone who cares that we're over an object in the table
	    objs = self.GetObj(x,y)
	    if len(objs) != 0:
		# Only do the top object
		for listener in self.listeners:
		    listener.Notify(objs[len(objs)-1])
	    else:
		for listener in self.listeners:
		    listener.Notify(None)
	elif self.reqCmd == TBL_PLACE_CARD:
	    self.placingCard.Move(x, y)
	    self.Redraw()
	elif self.reqCmd == TBL_DRAG_SELECT:
	    coord = self.rbsel[0] 
	    width = x - coord[0]
	    height = y - coord[1]
	    if len(self.rbsel) == 1:
		self.rbsel.append((width,height))
	    else:
		self.rbsel[1] = (width, height)
	    self.Redraw()
	elif self.reqCmd == TBL_DRAG_OBJS:
	    if len(self.curSelection) != 0:
		g = self.gridSize
		# calculate the delta from the original drag position
		if self.snapGrid:    
		    (dx, dy) = (int((x-self.dragOriginXY[0])/g)*g, int((y-self.dragOriginXY[1])/g)*g)
		else:
		    (dx, dy) = (x-self.dragOriginXY[0], y-self.dragOriginXY[1])
		
		for o in self.curSelection:    
		    if(self.snapGrid): #Align the object on the grid before we start
			o.dragOrigin = (int(o.dragOrigin[0]/g)*g,int(o.dragOrigin[1]/g)*g)
		    o.Move(o.dragOrigin[0]+dx,o.dragOrigin[1]+dy)
		
		self.Redraw()
	elif self.reqCmd == TBL_NEW_OBJECT:
	    if self.snapGrid:
		g = self.gridSize
		x = int(x/g)*g
		y = int(y/g)*g
		
	    self.newGUIObj.Move(x,y)
	    self.Redraw()

    def OnMouseLeave(self, event):
	if self.reqCmd == TBL_DRAG_OBJS:
	    bb = BlackboardMsg(self, BBM_DRAGOBJS, self.curSelection)
	    GLOBAL_Blackboard.addMessage(bb)
	    
	    dropCursor = wx.StockCursor(wx.CURSOR_QUESTION_ARROW)
	    wx.SetCursor(dropCursor)
	    
    def OnMouseEnter(self, event):
	if self.reqCmd == TBL_DRAG_OBJS:	    
	    bb = GLOBAL_Blackboard.find(BBM_DRAGOBJS)
	    if(bb):
		# If there's a drag message on the blackboard from us, remove it
		if(bb.getOwner() == self):
		    GLOBAL_Blackboard.removeMessage(bb)
	    
	    #normalCursor = wx.StockCursor(wx.CURSOR_ARROW)
	    #self.SetCursor(normalCursor)
	    print "returned"

    def OnLeftButtonEvent(self, event): 
	(x, y) = self.ConvertEventCoords(event)
	redraw = False
	processed = False
	
	objs = self.GetObj(x,y)
	if(len(objs) != 0):
	    for obj in objs:
		if(obj.HandleEvent(event)):
		    processed = True
	
	if(processed == True):
	    self.Redraw()
	    return
	
	if self.reqCmd == TBL_NO_CMD:
	    if event.LeftDown():
		objs = self.GetObj(x, y)
		if event.m_controlDown:
		    if(len(objs) != 0):
			o = objs.pop(0)
			# Only add the object to the current selection once
			if self.curSelection.count(o) == 0:
			    o.SetHighlighted(True)
			    self.curSelection.append(o)
			    redraw = True
		elif len(self.curSelection) == 0:
		    if len(objs) != 0:
			# If the shift key is down during a drag, it will pick up all
			# the objects in a stack. Otherwise, it just picks the top of the
			# Z-order
			if(event.m_shiftDown):
			    processObjs = objs
			else:
			    processObjs = [objs.pop()]
			    				
			for obj in processObjs:	
			    obj.dragOrigin = obj.GetXY() # Returns a tuple containing (x,y) of the object
			    self.MoveZOrder(obj, TBL_ZORDER_TOP)
			    obj.inSelect = True

			self.curSelection = processObjs 
			self.dragOffset = (x, y)
			self.dragOriginXY = (x, y)
			#self.CaptureMouse()
			self.reqCmd = TBL_DRAG_OBJS
		    else:
			self.rbsel.append((x,y));
			self.reqCmd = TBL_DRAG_SELECT
		else:
		    self.dragOffset = (x, y)		    
		    self.dragOriginXY = (x, y)
		    for obj in self.curSelection:
			obj.dragOrigin = obj.GetXY() # Returns a tuple containing (x,y) of the object
			self.MoveZOrder(obj, TBL_ZORDER_TOP)
		    self.reqCmd = TBL_DRAG_OBJS
	    elif event.LeftUp():
		# Check to see if we have a drag n drop set
		bb = GLOBAL_Blackboard.find(BBM_DRAGOBJS)
		if(bb):
		    accepted = []
		    objs = bb.getObjs()
		    px = x
		    py = y
		    for c in objs:
			if(isinstance(c, Card)):
			    print "Deck DragnDrop: Got a card"			    
			    c.parent = self # Change the parent association
			    accepted.append(c)
			    c.Move(px, py)
			    c.SetHighlighted(False) # Clear an highlighting from the Hand window
			    px = px + c.rect.width+5
		    
		    self.AddToTable(accepted)		    
		    self.Refresh()
		    bb_ret = BlackboardMsg(self, BBM_DRAGACCEPT, accepted)
		    bb.getOwner().OnDragDone(bb_ret) # Send an accept message back to owner
		    # Person who handles the event cleans up the Blackboard
		    GLOBAL_Blackboard.clearMessages()	
	elif self.reqCmd == TBL_NEW_OBJECT:
	    self.AddToTable(self.newGUIObj)
	    self.reqCmd = TBL_NO_CMD
	    
	    self.newGUIObj = None
	    redraw = True
	    
	elif self.reqCmd == TBL_DRAG_SELECT:
	    if event.LeftUp():
		start = self.rbsel[0]
		end = (x,y)
		objs = self.GetObjsInRect(start, end)
		# deselect any selected items before continuing
		if len(self.curSelection) != 0:
		    for o in self.curSelection:
			o.SetHighlighted(0)
		self.curSelection = objs
		for o in objs:
		    o.SetHighlighted(1)
		# clear the selection rectangle
		self.rbsel = []
		self.reqCmd = TBL_NO_CMD
		redraw=True
	elif self.reqCmd == TBL_DRAG_OBJS:	    
	    if event.LeftUp():
		redraw = self.HandleDragEnd(x,y)
		
	if redraw:
	    self.Redraw()

    def HandleDragEnd(self, x, y):
	# Generate the network message
	if(GLOBAL_NetManager.ready):	   
	    for o in self.curSelection:
		m = DecknetMessage()
		m.type = 5
		m.x=o.GetX()
		m.y=o.GetY()
		m.uid = o.uid
		GLOBAL_NetManager.sendMessage(m)
	    
	# See what we're dropping on
	objs = self.GetObj(x, y)
	# Take out anything in the current selection from consideration
	for o in objs:
	    if o in self.curSelection:
		objs.remove(o);
		
	if len(objs) != 0:
	    o = objs.pop()
	    # Figure out what the drop target wants to keep
	    acceptedObjs = o.DropObjs(self.curSelection)
	    # Remove the items the drop target accepted from the table
	    if(len(acceptedObjs)>0):
		self.Remove(acceptedObjs)

	# Deselect everything that was in the selection and
	#   stick the current selection items back on the table
	for o in self.curSelection:
	    o.SetHighlighted(0)
	    o.inSelect = False
	
	self.curSelection = []
	self.reqCmd = 0
	return(True) # Indicates a redraw

    def OnRightButton(self, event):
	(x, y) = self.ConvertEventCoords(event)
	
	objList = self.GetObj(x,y)
    
	if(len(objList) > 0):
	    amenu = ActionMenu(self, event.GetPosition(), objList.pop() , self.curSelection)
	    # TODO: Fix the refresh to be limited to the obj that requested the refresh
	    # TODO: Make the menu item tell the table if it needs to redraw or not
	else:
	    amenu = ActionMenu(self, event.GetPosition(), self, [])
	    
	self.Refresh()

    def GetPopupMenu(self):
	popup = wx.Menu()
	popup.Append(10, "Show Grid")
	popup.Append(11, "Snap To Grid")
	
	actionHash = { 10:(Table.OnShowGrid,False), 11:(Table.OnSnapToGrid,False)}
	
	return (popup, actionHash)    	
	    
    def OnShowGrid(self):
	if self.showGrid:
	    self.showGrid = False
	else:
	    self.showGrid = True
	
	self.Redraw()
    
    def SetGridSize(self,event):
	dlg = AskDialog(self, -1, "Size")
	if(dlg.ShowModal()==0):
	    self.gridSize = 10
	else:
	    if(dlg.result != ""):
		self.gridSize = int(dlg.result)
	    else:
		self.gridSize = 10
	print dlg.result
	self.Redraw()
	
    def OnSnapToGrid(self):
	if self.snapGrid:
	    self.snapGrid = False
	else:
	    self.snapGrid = True
	    g = self.gridSize
	    for o in self.gfxObjs:
		o.SetX(int(o.GetX()/g)*g)	
		o.SetY(int(o.GetY()/g)*g)
	    self.Redraw()

    def OnDragDone(self, msg):
	print "Drag was received"
	if(msg.getType() == BBM_DRAGACCEPT):
	    # Window reports which objects from the drag were accepted.
	    # Remove those from the table and leave the rest
	    removeList = []
	    for c in msg.getObjs():
		removeList.append(c)
		c.SetHighlighted(False) # If we did a drag select, those objects will be highlighted
		
	    if(len(removeList) != 0):
		self.Remove(removeList)
	    # Anything that was rejected (ie, not on the remove list) should be put back
	    # where we grabbed it from
	    for item in removeList:
		self.curSelection.remove(item)
	    for obj in self.curSelection:
		#coord = self.dragOrigin.get(obj)
		obj.Move(obj.dragOrigin[0], obj.dragOrigin[1])
	
	for o in self.curSelection:
	    o.SetHighlighted(False)
	self.curSelection = []
	self.reqCmd = TBL_NO_CMD
	self.Redraw() 
   
    def DoDrawing(self, dc, printing=False):
	dc.BeginDrawing()
	dc.Clear()
	if self.showGrid:
	    dc.SetPen(wx.LIGHT_GREY_PEN)
	    for x in range(0,self.maxWidth, self.gridSize):
		dc.DrawLine(x, 0, x, self.maxHeight)
	    for y in range(0,self.maxHeight, self.gridSize):
		dc.DrawLine(0, y, self.maxWidth, y)

	dc.SetPen(wx.Pen('BLUE', 1))
	# Draw all the stuff on the table
	for o in self.gfxObjs:
	    o.Draw(dc)
	# Draw anything currently moving
	for o in self.moveObjs:
	    o.Draw(dc)
	# Draw any new object
	if(self.newGUIObj != None):
	    self.newGUIObj.Draw(dc)
	# Draw the selection rectangle
	if self.reqCmd == TBL_DRAG_SELECT:
	    brush = wx.Brush('WHITE', wx.TRANSPARENT)
	    dc.SetBrush(brush)
	    dc.SetPen(wx.Pen('BLACK', 1))
	    dc.DrawRectangle(self.rbsel[0][0],self.rbsel[0][1], self.rbsel[1][0],self.rbsel[1][1])
	dc.EndDrawing()
 
class Hand(Surface):
    def __init__(self, parent,  id, size = wx.DefaultSize):
	Surface.__init__(self, parent, id, 1000, 100, size)
	
	self.cards = []
	self.curSelection = []
	self.reqCmd = TBL_NO_CMD
	self.curObj = None 
	self.pickCoord = None
	
	self.SetScrollbars(10, 10, self.maxWidth/10, self.maxHeight/10)
	
	wx.EVT_PAINT(self, self.OnPaint)	
	wx.EVT_ENTER_WINDOW(self, self.OnMouseEnter)
	wx.EVT_LEAVE_WINDOW(self, self.OnMouseLeave)
	wx.EVT_LEFT_DOWN(self, self.OnLeftButtonEvent)	
	wx.EVT_LEFT_UP(self, self.OnLeftButtonEvent)
	wx.EVT_RIGHT_UP(self, self.OnRightButtonEvent)
   	wx.EVT_MOTION(self, self.OnMouseMove)
	wx.EVT_KEY_DOWN(self, self.OnKeyDown)
	
    def OnKeyDown(self, event):
	if(len(self.curSelection) == 1):
	    if event.GetKeyCode() == wx.WXK_LEFT:
		self.MoveZOrder(self.curSelection[0], TBL_ZORDER_PREV);
	    elif event.GetKeyCode() == wx.WXK_RIGHT:
		self.MoveZOrder(self.curSelection[0], TBL_ZORDER_NEXT);		
	    self.Refresh()
	    
	
    def OnMouseMove(self, event):
	(x,y) = self.ConvertEventCoords(event)
	if self.reqCmd == TBL_NO_CMD:
	    # Tell anyone who cares that we're over an object in the table
	    objList = self.GetObj(x,y)
	    if len(objList) != 0:
		# only do the top object, if obj is None, then the listeners will
		# be notified of the fact since obj == None.
		obj = objList.pop()
	    else:
		obj = None
	    for listener in self.listeners:
		listener.Notify(obj)
	    	    
	elif self.reqCmd == TBL_DRAG_OBJS:
	    pass	
		    
    def OnMouseEnter(self, event):
	if(self.reqCmd == TBL_NO_CMD):
	    bb = GLOBAL_Blackboard.find(BBM_DRAGOBJS)    
	    if(bb):
		# This could be our drag event, check it and nuke it from the blackboard
		if(bb.getOwner() == self): 
		    GLOBAL_Blackboard.removeMessage(bb)
		else:
		    print "Some objects are being dragged"

    def OnMouseLeave(self, event):	
	if self.reqCmd == TBL_DRAG_OBJS:
	    print "Mouse left"
	    bb = BlackboardMsg(self, BBM_DRAGOBJS, self.curSelection)
	    GLOBAL_Blackboard.addMessage(bb)
	    
	    #dropCursor = wx.StockCursor(wx.CURSOR_QUESTION_ARROW)
	    #self.SetCursor(dropCursor)
	
    def CardSelectToggle(self, x, y):
	obj = self.GetObj(x, y)
	if(obj != None):		
	    obj.SetHighlighted(not obj.inSelect)
	    if(obj in self.curSelection):
		self.curSelection.remove(obj)
	    else:
		self.curSelection.append(obj)
	
    def OnLeftButtonEvent(self, event):
	(x, y) = self.ConvertEventCoords(event)
	if(event.LeftUp()):
	    if(self.reqCmd == TBL_NO_CMD):
		bb = GLOBAL_Blackboard.find(BBM_DRAGOBJS)
		if(bb):
		    accepted = []
		    objs = bb.getObjs()
		    for c in objs:
			if(isinstance(c, Card)):
			    c.parent = self # Change the parent affiliation
			    self.gfxObjs.append(c)
			    accepted.append(c)
		    self.Refresh()
		    bb_ret = BlackboardMsg(self, BBM_DRAGACCEPT, accepted)
		    bb.getOwner().OnDragDone(bb_ret) # Send an accept message back to owner
		    # Person who handles the event cleans up the Blackboard
		    GLOBAL_Blackboard.clearMessages()		    
			
	    elif(self.reqCmd == TBL_DRAG_OBJS):
		#obj = self.GetObj(x,y)
		dist = x-self.pickCoord[0]
		cardMoveDist = dist/60
		
		for o in self.curSelection:
		    o.SetHighlighted(False)
		self.curSelection = []
		self.reqCmd = TBL_NO_CMD
		self.Refresh()
		#self.Remove(self.curSelection)
		#if(obj in self.gfxObjs):
		#    i = self.gfxObjs.index(obj)
		#    self.gfxObjs.insert(i+1,self.curSelection)
		#    self.curSelection = []
		#    self.Refresh()
		#    self.reqCmd = TBL_NO_CMD
		
	elif(event.LeftDown()):
	    objList = self.GetObj(x,y)
	    if(len(objList) != 0):
		if event.m_controlDown:
		    obj = objList[0]
		    obj.SetHighlighted(not obj.inSelect)
		    if obj in self.curSelection:
			self.curSelection.remove(obj)
		    else:
			self.curSelection.append(obj)
		else:
		    obj = objList.pop()	
		    if obj not in self.curSelection:
			self.curSelection.append(obj)
			obj.SetHighlighted(True)
		    self.pickCoord = (obj.GetX(),obj.GetY()) # Get the upper left hand corner of the obj as the pick point	
		    self.reqCmd = TBL_DRAG_OBJS
		self.Refresh()
	    else:
		for o in self.curSelection:
		    o.SetHighlighted(False) 
		self.curSelection = []
		self.Refresh()
		print "Hand: No objects to grab"
	       
    def OnRightButtonEvent(self, event):
	(x, y) = self.ConvertEventCoords(event)

	objList = self.GetObj(x, y)
	if(len(objList) > 0):
	    obj = objList[0]
	    amenu = ActionMenu(self, event.GetPosition(), obj , self.curSelection)

	    for listener in self.listeners:
		listener.Refresh(obj)	
	# TODO: Fix the refresh to be limited to the obj that requested the refresh
	# TODO: Make the menu item tell the table if it needs to redraw or not
	self.Refresh()
		
    def Remove(self, objs):	
	for o in objs:
	    print o.name
	    if isinstance(o, Card):
		self.gfxObjs.remove(o)
	self.Refresh()
	
    def OnDragDone(self, msg):
	print "In drag done"
	if(msg.getType() == BBM_DRAGACCEPT):
	    print "dragaccept"
	    removeList = []
	    for c in msg.getObjs():
		if(isinstance(c, Card)):
		    print "Adding to Hand remove list"
		    removeList.append(c)
	    self.Remove(removeList)
	    self.curSelection = []
	    self.reqCmd = TBL_NO_CMD
	    print "Hand: Drag was received"
	
    def DoDrawing(self, dc, printing=False):
	dc.BeginDrawing()
	dc.Clear()
	dc.SetPen(wx.Pen('BLUE', 1))
	x = 10
	# Draw any cards
	for c in self.gfxObjs:
	    c.Move(x, 10)
	    x = x + c.rect.width+10
	    c.Draw(dc)

	dc.EndDrawing()

class CardInfo(wx.TextCtrl):
    def __init__(self, parent, ID, title="", pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.TE_MULTILINE, validator=wx.DefaultValidator, name=wx.TextCtrlNameStr):
	wx.TextCtrl.__init__(self, parent, ID, title, pos, size, style,validator,name)
	
	self.displayItem = None
	self.dirty = False
	
    def Notify(self, msg):	
	if(msg == None):
	    self.displayItem = None
	    self.SetValue("")
	else:
	    if(isinstance(msg, Card)):
		if(self.displayItem != msg):
		    self.displayItem = msg
		    data = self.GetDisplayData(msg)
		    self.SetValue(data)
    
    def Refresh(self, obj):
	if(isinstance(obj, Card)):
	    self.SetValue(self.GetDisplayData(obj))

    def GetDisplayData(self, card):
	if(card.facing == FACE_UP):
	    cardData = card.peer
	    data = "Title:"+cardData.title+"\n"
	    data = data+ "Desc:"+ cardData.description+"\n"
	    data = data + "Attrs:\n"
	    for attr in cardData.attrs.keys():
		data = data + attr + ": " + cardData.attrs[attr]+"\n"
	    return(data)
	else:
	    return("")
	
class CardListDialog(wx.Dialog):
    def __init__(
            self, parent, ID, title, size=wx.DefaultSize, pos=wx.DefaultPosition, 
            style=wx.DEFAULT_DIALOG_STYLE, cardList=None
            ):
	
	self.parent = parent
	
        # Instead of calling wx.Dialog.__init__ we precreate the dialog
        # so we can set an extra style that must be set before
        # creation, and then we create the GUI dialog using the Create
        # method.
        pre = wx.PreDialog()
        pre.Create(parent, ID, title, pos, size, style)

        # This next step is the most important, it turns this Python
        # object into the real wrapper of the dialog (instead of pre)
        # as far as the wxPython extension is concerned.
        self.this = pre.this

        # Now continue with the normal construction of the dialog
        # contents
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        label = wx.StaticText(self, -1, "Cards")
        sizer.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

	# List all of the available cards in the list box
	cardList = []
	for crd in dm.cards.values():
	    cardList.append(crd.title)
	self.list = wx.ListBox(self, -1, size=(200,300), choices=cardList)
        sizer.Add(self.list, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        line = wx.StaticLine(self, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)

        btn = wx.Button(self, 101, " Add ")
        btn.SetDefault()
        box.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
	self.Bind(wx.EVT_BUTTON, self.AddCard, btn)

        btn = wx.Button(self, wx.ID_CANCEL, " Close ")
        box.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        sizer.Add(box, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.SetSizer(sizer)
        self.SetAutoLayout(True)
	sizer.Fit(self)

    def OnCancel(self, event):
	self.Hide()

    def AddCard(self, event):
	cardName = self.list.GetStringSelection()
	if cardName != None:
	    cardData = dm.cards[cardName]
	    _uid = GLOBAL_UIDGen.GetNextUID() # Give the card some unique ID 
	    newCard = Card(cardData.title, 0, 0, self.parent.table, peer = cardData, uid=_uid)
	    self.parent.table.AddToTable(newCard)	

class ChatWindow(wx.Panel):
    def __init__(self, parent, ID, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.NO_BORDER, name="chat"):
	wx.Panel.__init__(self, parent, ID, pos, size, style, name)

	self.netParent = None

	sizer = wx.BoxSizer(wx.VERTICAL)
	
	self.chatWnd = wx.TextCtrl(self, 1, value="", size=(200, -1), style=wx.TE_MULTILINE)
	self.entryWnd = wx.TextCtrl(self, 2, value="", size=(200, 60), style=wx.TE_MULTILINE)

	sizer.Add(self.chatWnd, 1, wx.ALIGN_CENTRE | wx.ALL|wx.EXPAND)
	sizer.Add(self.entryWnd, 0, wx.ALIGN_CENTRE | wx.ALL|wx.EXPAND)
	
	self.SetSizer(sizer)
	self.SetAutoLayout(True)
	sizer.Fit(self)
	
	# Let the main window process the text entry's enter event
	self.Bind(wx.EVT_TEXT, self.HandleText, self.entryWnd)

    # Set the obj who has the net objects we should be talking to
    # in this case, the DeckardFrame
    def SetNetParent(self, parent):
	self.netParent = parent

    def HandleText(self, event):
	text = self.entryWnd.GetValue()
	if(text.endswith("\n")):
	    self.chatWnd.AppendText(text)
	    text= text.strip()
	    d = DecknetMessage()
	    d.type = 1
	    d.text = str(text)
	    
	    GLOBAL_NetManager.sendMessage(d)

	    self.entryWnd.SetValue("")

    def HandleNetMessage(self, m, peer):
	"""
	Handles a network message for the chat window
	m is the message itself
	peer is the peer that generated it
	"""
	self.chatWnd.AppendText(m.text)
	self.chatWnd.AppendText("\n")

class NetThread(Thread):
    def __init__(self, group=None, target=None, name="", args=(), kwargs={}):
	Thread.__init__(self, group, target, name, args, kwargs)
	
	self.go = True
	self.peer = None
	self.handlerObj = None
	self.listeners = {} # registered callbacks for message types

    def RegisterHandler(self, mtype, callback):
	if(not self.listeners.has_key(mtype)):
	    self.listeners[mtype] = []
	    
	handlerList = self.listeners[mtype]
	handlerList.append(callback)

    def SetPeer(self, peer):
	self.peer = peer
	
    def stop(self):
	self.go = False

    def run(self):
	while(self.go):
	    m = self.peer.next_message()
	    if m:
		print m.name
		handlerList = self.listeners[m.type]
		if(len(handlerList) > 0):
		    for handler in handlerList:
			handler(m,self.peer)
		print "Gots me a message"
	    sleep(0.1) # Give the thread a bit of break

class NetManager:
    def __init__(self):	
	self.ready = False
	self.listenThread = NetThread()
	self.peer = None
	self.msgList = []

    def RegisterHandler(self, mtype, callback):
	self.listenThread.RegisterHandler(mtype, callback)

    def Listen(self):
	if(self.peer == None):
	    self.peer = Peer(NET_MESSAGES)
	    self.peer.listen()
	    self.listenThread.SetPeer(self.peer)
	    self.listenThread.start()
	    self.ready = True
	else:
	    print "Net stuff already going"

    def Connect(self, addr="127.0.0.1"):
	if(self.peer == None):
	    self.peer = Peer(NET_MESSAGES)
	    self.peer.connect((addr, 9000))
    	    self.listenThread.SetPeer(self.peer)
	    self.listenThread.start()
    	    self.ready = True
	else:
	    print "Net stuff already going"

    def Cleanup(self):
	self.listenThread.stop()	

    def SetPeer(self, peer):
	self.peer = peer
	self.listenThread.SetPeer(peer)

    def sendMessage(self, m):
	"""
	Adds a message to the message queue
	This adds the default recipient to the message before placing it in the queue
	"""
	# Needs to use locks and stuf like that
	# But for now, thread safe be damned!!!	
	if(self.ready):
	    print "Sending the message", m.type
	    m.rcpt = self.peer.sks.keys()[0]
	    self.peer.send_message(m)

    def Reflect(self, obj, key, value):
	if(self.ready):
	    m = DecknetMessage()
	    m.type = 7
	    m.uid = obj.uid
	    m.key = key
	    m.value = pickle.dumps(value)
	    self.sendMessage(m)

GLOBAL_NetManager = NetManager()

class DeckardFrame(wx.Frame):    
    def __init__(self, parent, ID, title, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE):
	wx.Frame.__init__(self, parent, ID, title, pos, size, style)	

	self.CreateSplitterWnds()
	self.CreateMenus()
	
	# Card selection dialog box 
	self.cardMenu = None

	# Network stuff
	self.netPeer = None

	# Add the special listeners
	self.table.AddListener(self.cardInfo)
	self.hand.AddListener(self.cardInfo)
	
	# Menu Events
	wx.EVT_MENU(self, 110, self.OnCloseWindow)
	wx.EVT_MENU(self, 111, self.table.SetGridSize)
		
	wx.EVT_MENU(self, 202, self.DoDeck)
	wx.EVT_MENU(self, 203, self.DoCardmenu)
	wx.EVT_MENU(self, 204, self.DoCounter)
	wx.EVT_MENU(self, 205, self.DoRNG)
	wx.EVT_MENU(self, 206, self.DoMarker)

	wx.EVT_CLOSE(self, self.OnCloseWindow)

	self.RegisterNetEvents()

	# Build the Toolbar
	self.toolBar = self.CreateToolBar()
	wxb = wx.Bitmap("res/newcard.bmp")	
	self.toolBar.AddSimpleTool(10,wxb, "New Card", "New Card")
	wxb = wx.Bitmap("res/newdeck.bmp")	
	self.toolBar.AddSimpleTool(11,wxb, "New Deck", "New Deck")

	wxb = wx.Bitmap("res/debug1.bmp")	
	self.toolBar.AddSimpleTool(12,wxb, "Debug1", "Debug1")
	
	self.toolBar.AddSeparator()
	self.toolBar.Realize()
	
	# Toolbar events
	wx.EVT_TOOL(self, 10, self.OnToolClick)
	wx.EVT_TOOL(self, 11, self.OnToolClick)
	wx.EVT_TOOL(self, 12, self.OnToolClick)

    def RegisterNetEvents(self):
	# Register chat messages to the chat window
	GLOBAL_NetManager.RegisterHandler(1, self.chatWindow.HandleNetMessage)
	GLOBAL_NetManager.RegisterHandler(3, self.HandleNetMessage)
	GLOBAL_NetManager.RegisterHandler(4, self.table.NetAddCard)
	GLOBAL_NetManager.RegisterHandler(5, self.table.NetMoveObj)
	GLOBAL_NetManager.RegisterHandler(6, self.table.NetAddObj)
	GLOBAL_NetManager.RegisterHandler(7, self.table.NetObjState)
	GLOBAL_NetManager.RegisterHandler(8, self.table.NetRemoveObj)
	GLOBAL_NetManager.RegisterHandler(9, self.table.NetAddCardToDeck)
	GLOBAL_NetManager.RegisterHandler(10, self.table.NetRemoveCardFromDeck)
	
    def CreateSplitterWnds(self):
	# Create all the window panes and splitters  
	self.splitter = wx.SplitterWindow(self, -1)
	
	sw_left = wx.SplitterWindow(self.splitter, 1)
	self.table = Table(sw_left, -1)
	self.hand = Hand(sw_left, -1)
	sw_left.SplitHorizontally(self.table, self.hand, -130)
	sw_left.SetMinimumPaneSize(50) # Don't let people close the panes

	sw_right = wx.SplitterWindow(self.splitter, 2)
	self.chatWindow = ChatWindow(sw_right, 3)
	self.chatWindow.SetNetParent(self)
	self.cardInfo = CardInfo(sw_right, 4)
	sw_right.SplitHorizontally(self.chatWindow, self.cardInfo)
	sw_right.SetMinimumPaneSize(50) # Don't let people close the panes
	
	self.splitter.SplitVertically(sw_left, sw_right, -300)
	self.splitter.SetMinimumPaneSize(50)  # Don't let people close the panes	

    def CreateMenus(self):
	# Create the Menubar
	menuBar = wx.MenuBar()
	fileMenu = wx.Menu()
	fileMenu.Append(111, "Set Grid Size")
	fileMenu.Append(110, "Exit")
	menuBar.Append(fileMenu, "File")

	# Object Menu
	objMenu = wx.Menu()
	objMenu.Append(202, "Do Deck")
	objMenu.Append(203, "Show Card Menu")
	objMenu.Append(204, "Do Counter")
	objMenu.Append(205, "Do RNG")
	objMenu.Append(206, "Do Marker")
	menuBar.Append(objMenu, "Objects")

	cardListMenu = wx.Menu()
	cardcnt = 1
	for crd in dm.cards.values():
	    cardListMenu.Append(204+cardcnt, crd.title)
	    cardcnt = cardcnt + 1
	objMenu.AppendMenu(42, "Card List", cardListMenu)

	deckListMenu = wx.Menu()
	deckcnt = 1
	for deck in dm.decks.values():
	    deckListMenu.Append(204+cardcnt+deckcnt, deck.name)
	    deckcnt = deckcnt + 1
	objMenu.AppendMenu(42, "Deck List", deckListMenu)

	# Net menu
	netMenu = wx.Menu()
	netMenu.Append(401, "Set ID (testing)")
	netMenu.Append(402, "Listen")
	netMenu.Append(403, "Connect")
	
	menuBar.Append(netMenu, "Net")	
	# Net events
	wx.EVT_MENU(self, 401, self.SetID)
	wx.EVT_MENU(self, 402, self.ListenPeer)
	wx.EVT_MENU(self, 403, self.ConnectPeer)
	
	self.SetMenuBar(menuBar)

    def DoCardmenu(self, event):
	if(self.cardMenu == None):
	    self.cardMenu = CardListDialog(self, -1, "Card Selection", size=(350, 200), style = wx.DEFAULT_DIALOG_STYLE)
	    self.cardMenu.CenterOnScreen()    
	    self.cardMenu.Show()    
	else:
	    self.cardMenu.Show()

    def DoDeck(self, event):
	name = "deck" +str(self.table.curDeckCnt)
	self.table.curDeckCnt = self.table.curDeckCnt + 1
	uid = GLOBAL_UIDGen.GetNextUID()
	self.table.newGUIObj = Deck(name, 0, 0, self.table, _uid=uid)
	self.table.reqCmd = TBL_NEW_OBJECT
    
    def DoCounter(self, event):
	uid = GLOBAL_UIDGen.GetNextUID()
	self.table.newGUIObj = Counter("counter", 0, 0, self.table, _uid=uid)	    
	self.table.reqCmd = TBL_NEW_OBJECT
    
    def DoRNG(self, event):
	uid = GLOBAL_UIDGen.GetNextUID()
	self.table.newGUIObj = RNG("rng", 0, 0, self.table, _uid=uid)	    
	self.table.reqCmd = TBL_NEW_OBJECT

    def DoMarker(self, event):
	uid = GLOBAL_UIDGen.GetNextUID()
	self.table.newGUIObj = Marker("marker", 0, 0, self.table, _uid=uid)	    	
	self.table.reqCmd = TBL_NEW_OBJECT
	
    def SetID(self, event):
	dlg = AskDialog(self, -1, "Set UID Base")
	if(dlg.ShowModal()):
	    GLOBAL_UIDGEN = UIDGen(int(dlg.result))
	
    def ListenPeer(self, event):
	GLOBAL_NetManager.Listen()
	
    def ConnectPeer(self, event):
	dlg = AskDialog(self, -1, "IP Address")
	if(dlg.ShowModal()==0):
	    addr = "127.0.0.1"
	else:
	    if(dlg.result != ""):
		addr = dlg.result
	    else:
		addr = "127.0.0.1"
	print "Address=", addr

	GLOBAL_NetManager.Connect(addr)
	
	# Send a howdy-do
	m = DecknetMessage()
	m.type = 3
	m.nick = "Goober"
	GLOBAL_NetManager.sendMessage(m)

    def HandleNetMessage(self, m, peer):
	"""
	Handles a net message for the frame
	m is the incoming message
	peer is the Network peer that received it
	"""
	
	print "Got a hello from ", m.nick

    def OnToolClick(self, event):
	if event.GetId() == 10:
	    self.DoCardmenu(None)
	    #self.table.reqCmd = TBL_DRAW_CARD
	elif event.GetId() == 11:
	    self.DoDeck(None)
	elif event.GetId() == 12:
	    self.DoDebug1()

    def DoDebug1(self):
	# Lay down some cards
	cardData = dm.cards['Volcano']
	obj = Card(cardData.title, 0, 0, self.table, peer = cardData, uid=GLOBAL_UIDGen.GetNextUID())	    
	self.table.AddToTable(obj, False)
	cardData = dm.cards['Flood']
	obj = Card(cardData.title, 0, 0, self.table, peer = cardData, uid=GLOBAL_UIDGen.GetNextUID())	    
	self.table.AddToTable(obj, False)
	cardData = dm.cards['Locusts']
	obj = Card(cardData.title, 0, 0, self.table, peer = cardData, uid=GLOBAL_UIDGen.GetNextUID())	    
	self.table.AddToTable(obj, False)

	self.table.Redraw()

    def OnCloseMe(self, event):
	self.Close(True)
    
    def OnCloseWindow(self, event):
	GLOBAL_NetManager.Cleanup()
	self.Destroy()
    	
class DeckardApp(wx.App):
    def OnInit(self):
	if DO_SPLASH == 1:
	    bitmap = wx.Bitmap("deckard.bmp")
	    if (bitmap):
		wx.SplashScreen(bitmap,wx.SPLASH_CENTRE_ON_SCREEN|wx.SPLASH_TIMEOUT, 6000, None, -1, wx.DefaultPosition, wx.DefaultSize, wx.SIMPLE_BORDER|wx.STAY_ON_TOP);
		wx.Yield();
	
	# Load up all those fancy graphics file format handlers
	wx.InitAllImageHandlers()
	
	self.frame = DeckardFrame(None, -1, "Deckard Alpha", size=(750, 600),style = wx.DEFAULT_FRAME_STYLE)# |  wxFRAME_TOOL_WINDOW )
	self.frame.Show()
	self.SetTopWindow(self.frame)
	return True

def handleArgs(app, dm):
    done = False

    idx = 1
    process_args = 1
    process_deck = 2
    set_id = 3

    state = process_args

    while(idx < len(sys.argv)):
	arg = sys.argv[idx]
	if(state == process_args):
	    if arg[0] == '-':
		if(arg[1] == 'd'):
		    # Deck argument
		    idx = idx + 1
		    state = process_deck
		elif(arg[1:] == 'id'):
		    idx = idx + 1
		    state = set_id
		else:
		    print "Unprocessed arg: ", arg
		    idx = idx + 1
	    else:
		print "Unprocessed option: ", arg
		idx = idx +1
	elif(state == process_deck):
	    print "Adding deck ", arg
	    dm.loadXML(arg)
	    idx = idx + 1
	    state = process_args
	elif(state == set_id):
	    print "Setting ID ", arg
	    id = int(arg)
	    GLOBAL_UIDGen.SetUID(id)
	    idx=idx+1
	    state = process_args
	    
def main():
    # Import Psyco if available
    #try:
        #import psyco
        #psyco.full()
    #except ImportError:
#	print "Unable to use psyco"
    
    global dm
    dm = DeckManager()

    app = DeckardApp(0)
    handleArgs(app, dm)
    
    #for arg in sys.argv[1:]:
    #	dm.loadXML(arg)
    
    app.MainLoop()
    
if __name__ == '__main__':
    main()

