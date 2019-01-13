CXX=g++
CXXFLAGS=-I/opt/clanlib-0.6.1/include -I../coldet/src -c -g -Wall
LDFLAGS=-L/opt/clanlib-0.6.1/lib -L../coldet/src -lclanTTF -lclanCore -lclanDisplay -lclanApp -lclanGL -lcoldet

gl-mockup: gl-mockup.o
	$(CXX) $(LDFLAGS) -o $@ $<

gl-mockup.o: gl-mockup.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<
