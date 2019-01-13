"""
Networking utilities for Deckard and friends.
"""


from SimpleXMLRPCServer import SimpleXMLRPCServer
import types, time, thread, socket, xmlrpclib, sys

DEFAULT_PORT = 9000
TRANSPORT = 'http'

class DecknetError(Exception):
    """
    Exception thrown on various network errors. See the .msg field.
    """
    def __init__(self, msg="Decknet Error", root=None):
	self.root = root
	self.msg = msg

    def __str__(self):
	if self.root: return "%s:\n%s" % (self.msg, str(self.root))
	else: return self.msg

class NetManager:
    """
    """
    def __init__(self, port=9000, hostname=''):
	"""
	"""
	self.done = False
	self.listening = False
        self.port = port
        self.peers = {}
        self.hostname = hostname or socket.gethostname()
        self.username = ''

    #
    # Infrastructure methods
    #


    def _net_monitor(self, args):
	"""
	Thread executor. Creates an XMLRPC server and listens on it in
        a loop, terminating if instructed to via the self.done field.
        The XMLRPC server is passed 'self' to use for message callbacks.
	"""
	# lists exported methods for the benefit of the SimpleXMLRPCServer
	remote_methods = [(self.rpc_create_card, 'create_card'),
			  (self.rpc_remove_card, 'remove_card'),
			  (self.rpc_move_card, 'move_card'),
			  (self.rpc_hello, 'hello'),
			  (self.rpc_goodbye, 'goodbye')]

        try:
            svr = SimpleXMLRPCServer((self.hostname, self.port), logRequests=0)
	    for fun, name in remote_methods: svr.register_function(fun, name)
            self.listening = True
            while not self.done: (svr.handle_request() or 1) and time.sleep(0.1)
            self.listening = False
            svr.server_close()
        except Exception, e:
            print e

    def listen(self): thread.start_new_thread(self._net_monitor, (None,))

    def connect(self, host=None, port=None, uri=None):
        """
        Connects to the indicated client (via host/port or explicit URI.)
        If successful, sends the client a 'hello' message, and processes
        any return info (i.e. list of clients.) If any other clients
        returned by new peer are unknown to us, connects to them as well.
        """
        if not uri: uri = '%s://%s:%d/' % (TRANSPORT, host, (port or self.port))
        if not self.listening: self.listen()
        myuri = '%s://%s:%d/' % (TRANSPORT, self.hostname, self.port)
        try:
            pxy = xmlrpclib.ServerProxy(uri)
            pxy_user, others = pxy.hello(myuri, self.username)
        except socket.error, e:
            raise DecknetError(msg="Couldn't connect to %s" % uri, root=e)
        self.peers[pxy_user] = (uri, pxy)
        for peer_user, peer_uri in others:
            if self.peers.has_key(peer_user): continue
            peer_pxy = None
            try:
                peer_pxy = xmlrpclib.ServerProxy(peer_uri)
                peer_pxy.hello(myuri, self.username)
            except socket.error, e: continue
            self.peers[peer_user] = (peer_uri, peer_pxy)

    def rpc_hello(self, uri, username):
        """
        Handles a hello message from a remote client. This is the first
        method a remote client should send us; it includes a (requested)
        username and the uri of that client's XMLRPC server, for
        back-communication.  If the username is already known to us,
        return an empty list to the remote client as a signal that the
        name is invalid; otherwise, send it a list of all other peers we
        know about.
        """
        print '%s processing hello from %s@%s' % (self.username, username, uri)
        if self.peers.has_key(username): return []
        x = [(k, v[0]) for k, v in self.peers.items()]
        self.peers[username] = (uri, xmlrpclib.ServerProxy(uri))
        return (self.username, x)

    def rpc_goodbye(self, username):
        """
        Handles a goodbye message from a remote client. Just cleans
        up the client's connection, really.
        """
        if self.peers.has_key(username): del self.peers[username]
        return 0


    #
    # XMLRPC server callbacks
    #
    # Put code that handles messages from other clients into these functions.
    # Currently stubs.
    #

    def rpc_create_card(self, card_id, card_type):
        print '%s created %d as %d' % (self.username, card_id, card_type)
        return 42
    def rpc_remove_card(self, card_id):
        print '%s removed %d' % (self.username, card_id)
        return 43
    def rpc_move_card(self, card_id, x, y):
        print '%s moved %d to (%d, %d)' % (self.username, card_id, x, y)
        return 44


    #
    # Outgoing & control methods
    #
    # Put code that originates messages from local code to remote peers
    # in these functions.
    # Currently just stubs.
    #

    # connect(self, host, port, uri) is also a control method -- see above

    def shutdown(self):
        """
        Terminates the listening thread (if running) and says goodbye
        to all connected peers.
        """
        self.done = True
        for name, vals in self.peers.items():
            del self.peers[name]
            vals[1].goodbye(self.username)

    def send_msg(self):
        """
        Sample outgoing message.
        """
        for u, cxn in self.peers.items():
            print '%s sending to %s@%s' % (self.username, u, cxn[0])
            cxn[1].create_card(42, 142)

if __name__ == "__main__":
    print '***Instantiate...'
    p1 = NetManager(9001, 'localhost')
    p2 = NetManager(9002, 'localhost')
    p3 = NetManager(9003, 'localhost')

    print '***Name...'
    p1.username = 'foo'
    p2.username = 'bar'
    p3.username = 'baz'

    print '***Network...'
    sys.stdout.write('\tFoo:...')
    p1.listen()
    print 'done.'
    time.sleep(5)
    sys.stdout.write('\tBar:...')
    p2.connect(uri='http://localhost:9001/')
    print 'done.'
    time.sleep(1)
    sys.stdout.write('\tBaz:...')
    p3.connect(uri='http://localhost:9001/')
    print 'done.'

    time.sleep(3)

    print '***Transmit...'
    p1.send_msg()
    p2.send_msg()
    p3.send_msg()

    print '***Shutdown...'
    try:
        p1.shutdown()
        time.sleep(1)
	p2.send_msg()
	p3.send_msg()
        p2.shutdown()
        time.sleep(1)
        p3.shutdown()
    except Exception, e: print e
