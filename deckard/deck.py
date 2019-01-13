
import sys
from xml.sax import make_parser, handler, SAXException
from random import shuffle
import copy

class Deck:
    """
    Container class for cards; represents a list of cards (a deck).

     Attributes include:
     * name - value of the name='' attribute from XML
     * shuffle - if present as attr in XML, has that value; defaults to false
     * cards - list [] of cards contained in deck, either in order of
       appearance in XML, or random order if shuffle = true
     * back_image - default image to be used for backs of these cards
    """
    def __init__(self):
	# these all get set later in code, but init here to avoid exceptions
	self.name = ""
	self.shuffle = "false"
	self.back_image_file = ""
	self.cards = None

class Card:
    """
    Represents a card.

    Attributes:
    * attrs - any and all attributes from XML are added to this dict

    Hardcoded Attributes:
    These are attributes that are so common to all cards that they are expected
    to be present in all XML files.  These are NOT added to the attr dict
    above, but are instead added to self.__dict__ so that they can be used by
    other code as direct field references for convenience.

    * description - general description
    * title - name of the card, short summary, or whatever
    * image - image for front side of card
    * back_image - [optional] image for back of card - check with hasattr()
    """
    def __init__(self):
	# technically, these should all be in the XML and shouldn't need to
	# be set here; however, init them anyway so that they are at least
	# present if you forget in the XML; avoids runtime exceptions later
	self.title = ""
	self.description = ""
	self.attrs = {}
	self.image_file = ""
	self.back_image_file = None

class DeckManager(handler.ContentHandler):
    """
    The Deck and Card management class.

    This class is a SAX ContentHandler (from xml.sax.handler).  It contains
    the usual SAX handler callback methods, as well as a number of helper
    functions.  This class is self-polymorphic, and changes the set of helper
    functions in use to match the XML file it is loading.  That is, the
    default SAX callbacks only go far enough to determine whether the current
    file is a card-list or a deck, and then switches the helper functions over
    to the appropriate set for that XML element.
    """

    #
    # xml.sax Callbacks, nothing to see here, move along
    #
    def startElement(self, name, attrs):
	return self.doStartElement(name, attrs)

    def endElement(self, name):
	return self.doEndElement(name)
	
    def characters(self, chars):
	return self.doCharacters(chars)

    def startDocument(self):
	return self.doStartDocument()

    def endDocument(self):
	return self.doEndDocument()


    #
    # Constructor
    #
    def __init__(self):
	self.elt_stack = []
	self.char_dest = ()
	self.cards = {}
	self.decks = {}

	# initial handlers: these callbacks simply detect card-list or deck
	self.initHandlers = {
	    "doStartDocument": self.emptyStartDocument,
	    "doEndDocument": self.emptyEndDocument,
	    "doStartElement": self.detectXMLType,
	    "doEndElement": self.emptyEndElement,
	    "doCharacters": self.emptyCharacters
	}

	# initHandlers switches to these callbacks upon detecting card-list
	self.cardlistHandlers = {
	    "doStartElement": self.cardlistStartElement,
	    "doCharacters": self.cardlistCharacters,
	    "doEndElement": self.cardlistEndElement
	}

	# initHandlers switches to these callbacks upon detecting deck
	self.deckHandlers = {
	    "doStartElement": self.deckStartElement,
	    "doEndElement": self.deckEndElement,
	    "doCharacters": self.emptyCharacters
	}

	# general model here is update __dict__ with the appropriate callback
	# helpers, overwriting the previous values as required
	self.__dict__.update(self.initHandlers)

    #
    # xml.sax Callback Helpers
    #
    def emptyStartDocument(self):
	""" Self-explanatory; takes no action on this SAX event. """
	pass

    def emptyEndDocument(self):
	""" Self-explanatory; takes no action on this SAX event. """
	pass

    def detectXMLType(self, name, attrs):
	"""
	Detects whether the current file being parsed is a card-list or deck.
	"""
	if name not in ("card-list", "deck"): # SOMEONE SET UP US THE BOMB
	    print "unknown XML container '" + name + "', cannot continue"
	    raise SAXException("toplevel element unrecognized")
	else:
	    if name == "card-list":
		self.__dict__.update(self.cardlistHandlers)
	    else:
		self.__dict__.update(self.deckHandlers)

	    # relay this SAX event to the new helper set in case they need it
	    self.startElement(name, attrs)

    def cardlistStartElement(self, name, attrs):
	"""
	Helper callback for SAX startElement for the card-list parser.

	Note that duplicate cards (cards with the same string literal as
	title) will overwrite each other; last-occurring card will take
	precedence.
	"""
	if name not in ("card", "description", "attr"):
	    # this is not fatal here, just skip it
	    return

	if name == "card": # create a new card, copy attrs into it from XML
	    card = Card()
	    # note: this sets all *INLINE* attributes (NOT body child
	    # elements!) into __dict__ as fields; body child elements go into
	    # attrs dict, later
	    for pair in attrs.items():
		setattr(card, pair[0], pair[1])
	    # keep track of a stack of cards; technically this would imply
	    # that <card> is hierarchical (e.g. <card><card/></card>) which is
	    # nonsense, but we do this just in case
	    self.elt_stack.append(card);
	if name == "description":
	    # see cardlistCharacters()
	    card = self.elt_stack.pop()
	    self.char_dest = (card.__dict__, "description")
	    self.elt_stack.append(card)
	if name == "attr":
	    # handle an attr sub-element; add to the attrs dict in current card
	    card = self.elt_stack.pop()
	    if attrs.has_key("value"):
		card.attrs[attrs["name"]] = attrs["value"]
	    else:
		# again, see cardlistCharacters()
		self.char_dest = (card.attrs, attrs["name"])
	    self.elt_stack.append(card)

    def cardlistEndElement(self, name):
	"""
	Callback helper for SAX event endElement for card-list.
	"""
	if name == "card": # if we see a </card>, finalize current card
	    card = self.elt_stack.pop()
	    self.cards[card.title] = card # add it to the current dictionary
	if name == "card-list": # if </card-list>, reset to init handlers
	    self.__dict__.update(self.initHandlers)

    def deckStartElement(self, name, attrs):
	"""
	Helper callback for SAX startElement for the card-list parser.
	"""
	# this method is pretty analagous to cardlistStartElement
	if name not in ("deck", "card"): # again, not fatal
	    return

	# for decks, <card> is a reference to a card that must already have
	# been loaded (skip cards that don't exist) and only has one relevant
	# attribute: title
	if name == "card":
	    cardref = attrs["title"] # if card exists, add a copy to deck
	    if not self.cards.has_key(cardref):
		return
	    card = self.cards[cardref]
	    self.deck.cards.append(copy.deepcopy(card))
	if name == "deck": # instantiate a new Deck instance
	    self.deck = Deck()
	    for pair in attrs.items():
		setattr(self.deck, pair[0], pair[1])
	    # this sets the new deck's card list for use by card block, above
	    self.deck.cards = []
	    self.decks[attrs["name"]] = self.deck

    def emptyEndElement(self, name):
	""" Self-explanatory; takes no action on this SAX event. """
	pass

    def deckEndElement(self, name):
	"""
	Helper callback for SAX endElement for the card-list parser.

	Finalizes a deck-in-progress and adds it to the master list of decks
	"""
	if name == "deck":
	    # shuffle the deck if XML said to
	    if hasattr(self.deck, "shuffle") and self.deck.shuffle == "true":
		shuffle(self.deck.cards)
	    self.__dict__.update(self.initHandlers)

    def emptyCharacters(self, chars):
	""" Self-explanatory; takes no action on this SAX event. """
	pass

    def cardlistCharacters(self, chars):
        """
	SAX characters() event callback helper.
	"""
	# okay, so:  cardlistStartElement() above checks to see if the element
	# to be processed is non-singleton -- i.e. whether there is character
	# data that needs to be copied into the object. If there IS cdata,
	# then startElement sets the char_dest tuple to be a dictionary, and
	# the key in that dictionary to which the cdata is to be copied. This
	# method then retrieves the cdata and adds it to do the indicated dict
	# under the indicated key.
	if self.char_dest == ():  # if the tuple is empty, we don't care
	    return
	self.char_dest[0][self.char_dest[1]]= chars.strip()
	self.char_dest = ()

    #
    # Non-SAX-related utility function
    #
    def loadXML(self, filename):
	"""
	Loads the indicated XML file, parses it via SAX, and extracts the
	card-list or deck information.
	"""
	self.__dict__.update(self.initHandlers)
	# probably need a try block here: "future enhancement"
	parser = make_parser()
	parser.setContentHandler(self)
	parser.parse(filename)


# testbed function if this file is run as top-level; should not run on imports
if __name__ == "__main__":
    if len(sys.argv) < 2:
	print "no args; try giving me a list of XML files"
    else:
	dm = DeckManager()
	for arg in sys.argv[1:]:
	    dm.loadXML(arg)

	print "Cards:"
	for card in dm.cards.values():
	    print "\t" + card.title
	    print "\t\tImage: ", card.image_file
	    print "\t\tDescription: ", card.description
	    for attr in card.attrs.keys():
		print "\t\t" + attr + ": " + card.attrs[attr]

	for deck in dm.decks.values():
	    print "Deck: " + deck.name
	    print "\tShuffle: " + deck.shuffle
	    print "\tCards:"
	    for card in deck.cards:
		print "\t\t" + card.title
