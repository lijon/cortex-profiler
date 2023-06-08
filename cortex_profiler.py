#!/usr/bin/python3

# (C)2023 Jonatan Liljedahl - http://kymatica.com
#
# based on https://gist.github.com/ynsta/7df418cb27b908391f86

# TODO:
# - keyboard input to reset? maybe: press ctrl-C again to quit, any other key to reset?
# - instead of detecting ELF mtime change, it would be better to detect device reset via openocd if possible. maybe an option would be to have a separate "trigger file" that our vscode launch action can touch?
# - gracefully handle openocd server disconnect

import sys
import time
import os
import telnetlib
import subprocess
from bisect import bisect_right
import operator
import argparse

class UltimateHelpFormatter(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    pass

class OpenOCDCMSampler(object):

    def __del__(self):
        if self.net:
            cmd = b'exit\r\n'
            self.net.write(cmd)
            self.net.read_until(cmd, 1)
            self.net.close()

    def connect(self, host='localhost', port=4444):
        self.net = None
        self.net = telnetlib.Telnet(host, port)
        self.net.read_very_eager()

    def getpc(self):
        cmd = b'mrw 0xE000101C\r\n'
        self.net.write(cmd)
        res = self.net.read_until(b'\r\n\r> ', 1)

        if res:
            prefix = res[0:16]
            num    = res[16:-5]
            res    = res[-15:0]

            if prefix == cmd:
                return int(num,16)

        return 0


    def initSymbols(self, elf, readelf):
        proc = subprocess.Popen([readelf, '-sW', elf], stdout=subprocess.PIPE)
        self.elfmtime = os.path.getmtime(elf)
        self.table = []
        self.indexes = set()
        for line in iter(proc.stdout.readline, b''):
            field = line.decode('ascii').split()
            try:
                if field[3] == 'FUNC':
                    addr = int(field[1], 16)
                    func = field[7]
                    size = int(field[2])
                    if addr not in self.indexes:
                        self.table.append((addr, func, size))
                        self.indexes.add(addr)
            except IndexError:
                pass

        # find marked subsections of functions
        self.table.sort()
        parent = ''
        parentend = 0
        for i, (addr, symb, size) in enumerate(self.table):
            if size == 0 and addr < parentend:
                symb = symb[:symb.find("$uid")]
                self.table[i] = (addr, symb, parent)
            else:
                self.table[i] = (addr, symb, None)
                parent = symb
                parentend = addr+size
        
        self.addrs = [ x for (x, y, z) in self.table ]

    def func(self, pc):

        if pc == 0 or pc == 0xFFFFFFFF:
            return ('', 0, None)

        # find where pc lands between addresses, ignoring size
        i = bisect_right(self.addrs, pc)
        if i:
            addr, symb, parent = self.table[i-1]
            return (symb, addr, parent)

        return ('', 0, None)

def cli():

    help = '''A telnet connection to a running openocd server is used to sample the program counter.
A table of statistics is displayed that shows how often the CPU is executing inside each function.
    
Functions can be split up in sections for further detail by the use of this GCC macro,
which generates a FUNC symbol of size 0:

    #define FUNC_SYMB(l) asm(".thumb_func\\n" l "$uid%=:" :::)
    '''
    
    ap = argparse.ArgumentParser(description = "PC sampling profiler for ARM Cortex-M.", epilog=help, formatter_class=UltimateHelpFormatter)
    ap.add_argument("filename", help = "ELF file with symbols")
    ap.add_argument("-r","--rate", default=0.005, type=float, help = "sampling rate limit (seconds)")
    ap.add_argument("-i","--interval", default=1, type=float, help = "display update interval (seconds)")
    ap.add_argument("-l","--limit", default=50, type=int, help = "display the top N functions")
    ap.add_argument("-H","--host", default='localhost', help = "openocd telnet host")
    ap.add_argument("-p","--port", default=4444, type=int, help = "openocd telnet port")
    ap.add_argument("-e","--readelf", default="arm-none-eabi-readelf", help = "readelf command")
    args = ap.parse_args()

    sampler = OpenOCDCMSampler()
    elf = args.filename;
    sampler.initSymbols(elf, args.readelf)
    
    try:
        sampler.connect(args.host, args.port)
    except:
        print("Error: Could not connect to openocd server at",args.host,"port",args.port)
        print("Make sure you have a running instance of openocd and that the port matches.")
        exit(-1)

    ratelimit = args.rate
    interval = args.interval

    total = 0
    countmap = { }
    childmap = { }
    start = time.time()
    start0 = start

    try:
        while True:
            func, addr, parent = sampler.func((sampler.getpc()))

            if not addr:
                continue

            total += 1

            if parent:
                if parent not in childmap:
                    childmap[parent] = { }
                p = childmap[parent]
                
                if func not in p:
                    p[func] = 0
                p[func] += 1

                func = parent

            if func not in countmap:
                countmap[func] = 0                
            countmap[func] += 1                

            cur = time.time()
            if cur - start > interval:
                if os.path.getmtime(elf) > sampler.elfmtime:
                    total = 0
                    countmap = { }
                    childmap = { }
                    sampler.initSymbols(elf)
                    continue

                print ('\x1b[2J\x1b[H')
                tmp = sorted(countmap.items(), key=operator.itemgetter(1), reverse=True)
                tmp = tmp[:args.limit]
                for k, v in tmp:
                    print ('\x1b[90m> \x1b[96m{:05.2f}% \x1b[92m{}'.format((v * 100.) / total, k))
                    if k in childmap:
                        child = sorted(childmap[k].items(), key=operator.itemgetter(1), reverse=True)
                        for ck, cv in child:
                            print ('  \x1b[36m{:05.2f}%  \x1b[90m- \x1b[34m{}'.format((cv * 100.) / total, ck))
                start = cur
                print ()
                print ('\x1b[0m{} samples, {:05.2f} samples/second'.format(total, total/(cur-start0)))

            time.sleep(ratelimit)

    except KeyboardInterrupt:
        pass
