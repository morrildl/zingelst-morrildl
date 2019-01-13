import thread
l = thread.allocate_lock()
class foo(Exception): pass
def x():
    try:
	l.acquire()
	raise foo()
    except foo: print "Exception"
    finally: l.release()
