#!/usr/bin/env python3
"""Prototype exact-inode Unix-socket liveness scan across visible net namespaces.

Evidence helper only. It demonstrates the discriminator used by the investigation;
it is not proposed upstream code.
"""

import os
import sys
import time


def scan_socket_identities():
    seen_netns = set()
    live = set()
    errors = {}
    start = time.perf_counter_ns()

    with os.scandir('/proc') as entries:
        for entry in entries:
            if not entry.name.isdigit():
                continue

            base = f'/proc/{entry.name}'

            try:
                ns = os.stat(base + '/ns/net')
            except OSError as e:
                errors[('netns', e.errno)] = errors.get(('netns', e.errno), 0) + 1
                continue

            ns_id = (ns.st_dev, ns.st_ino)
            if ns_id in seen_netns:
                continue

            try:
                with open(base + '/net/unix', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
            except OSError as e:
                errors[('unix-table', e.errno)] = errors.get(('unix-table', e.errno), 0) + 1
                continue

            # Mark the namespace only after a successful table read. If this PID
            # disappears first, a later PID in the same namespace can still win.
            seen_netns.add(ns_id)

            for line in lines[1:]:
                fields = line.rstrip('\n').split(None, 7)
                if len(fields) < 8 or not fields[7].startswith('/'):
                    continue

                path = fields[7]
                try:
                    st = os.stat(base + '/root' + path, follow_symlinks=False)
                except OSError as e:
                    errors[('socket-path', e.errno)] = errors.get(('socket-path', e.errno), 0) + 1
                    continue

                live.add((st.st_dev, st.st_ino))

    elapsed = time.perf_counter_ns() - start
    return live, seen_netns, errors, elapsed


def main():
    live, namespaces, errors, elapsed = scan_socket_identities()
    print(f'elapsed_ns={elapsed}')
    print(f'parsed_netns={len(namespaces)}')
    print(f'live_socket_identities={len(live)}')
    print(f'errors={errors}')

    for path in sys.argv[1:]:
        try:
            st = os.stat(path, follow_symlinks=False)
        except OSError as e:
            print(f'{path}: stat-error={e.errno}')
            continue

        identity = (st.st_dev, st.st_ino)
        print(f'{path}: dev={st.st_dev} ino={st.st_ino} live={identity in live}')


if __name__ == '__main__':
    main()
