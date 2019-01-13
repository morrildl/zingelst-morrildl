CXX=g++
CXXFLAGS=-I/opt/clanlib-0.6.1/include -c -g -Wall
LDFLAGS=-L/opt/clanlib-0.6.1/lib -lclanTTF -lclanCore -lclanDisplay -lclanApp

hello: hello.o
	$(CXX) $(LDFLAGS) -o $@ $<

hello.o: hello.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<
