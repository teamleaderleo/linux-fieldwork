CC ?= cc
CFLAGS ?= -std=c11 -O2 -g -Wall -Wextra -Werror
LDLIBS ?= -ldl

all: vk_debug_report_repro vk_debug_utils_repro vk_allocator_instance_probe

vk_debug_report_repro: vk_debug_report_repro.c
	$(CC) $(CFLAGS) -o $@ $< $(LDLIBS)

vk_debug_utils_repro: vk_debug_utils_repro.c
	$(CC) $(CFLAGS) -o $@ $< $(LDLIBS)

vk_allocator_instance_probe: vk_allocator_instance_probe.c
	$(CC) $(CFLAGS) -o $@ $< $(LDLIBS)

clean:
	rm -f vk_debug_report_repro vk_debug_utils_repro vk_allocator_instance_probe
