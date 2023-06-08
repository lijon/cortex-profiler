# PC sampling profiler for Cortex-M MCUs

This script uses a telnet connection to a running openocd server to sample the program counter.
The PC sampling is fully non-intrusive and does not disturb the CPU while running.
It works also for the simpler Cortex-M models without SWO.

A table of statistics is displayed that shows how often the CPU is executing inside each function.

Functions can be split up in sections for further detail by the use of this GCC macro, which generates a FUNC symbol of size 0:

```c
#define FUNC_SYMB(l) asm(".thumb_func\\n" l "$uid%=:" :::)
```

Which can then be used like this:

```c
void foo(void) {
    FUNC_SYMB("a");
    // code here
    FUNC_SYMB("b");
    // more code here
    // etc..
}
```

## Installation

```
$ pip3 install git+https://github.com/lijon/cortex-profiler
```

Or download this repo and run `pip3 install .` in the directory.