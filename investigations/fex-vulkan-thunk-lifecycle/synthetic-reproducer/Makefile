CFLAGS ?= -O2 -g -fPIC -Wall -Wextra -Werror
CXXFLAGS ?= -O2 -g -std=c++20 -Wall -Wextra -Werror

all: libguest_thunk.so thunk_lifetime_repro

libguest_thunk.so: guest_thunk.c
	$(CC) $(CFLAGS) -shared -Wl,--build-id=none -o $@ $<

thunk_lifetime_repro: repro.cpp
	$(CXX) $(CXXFLAGS) -o $@ $< -ldl

clean:
	rm -f libguest_thunk.so thunk_lifetime_repro
