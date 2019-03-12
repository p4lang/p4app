p4app
=====

p4app is a tool that can build, run, debug, and test P4 programs. The
philosophy behind p4app is "easy things should be easy" - p4app is designed to
make small, simple P4 programs easy to write and easy to share with others.

Installation
------------

1. Install [docker](https://docs.docker.com/engine/installation/) if you don't
   already have it.

2. If you want, put the `p4app` script somewhere in your path. For example:

    ```
    cp p4app /usr/local/bin
    ```

That's it! You're done.

Usage
-----

p4app runs p4app packages. p4app packages are just directories with a `.p4app`
extension - for example, if you wrote a router in P4, you might place it in
`router.p4app`. Inside the directory, you'd place your P4 program, any
supporting files, and a `main.py` file that tells p4app how to run it.

This repository comes with an example p4app called [wire.p4app](examples/wire.p4app). Here's
how you can run it:

```
p4app run examples/wire.p4app
```

If you run this command, you'll find yourself at a Mininet command prompt. p4app
will automatically download a Docker image containing the P4 compiler and tools,
compile [wire.p4](examples/wire.p4app/wire.p4), and set up a container with a simulated network you
can use to experiment. In addition to Mininet itself, you can use `tshark`,
`scapy`, and the net-tools and nmap suites right out of the box.

That's pretty much it! There's one more useful command, though. p4app caches the
P4 compiler and tools locally, so you don't have to redownload them every time,
but from time to time you may want to update to the latest versions. When that
time comes, run:

```
p4app update
```

Creating a p4app package
------------------------

A p4app package has a directory structure that looks like this:

```
  my_program.p4app
    |
    |- main.py
    |
    |- my_program.p4
    |
    |- ...other files...
```

The `main.py` file is a Python script that tells p4app how to build and run a
P4 program; it's comparable to a Makefile. Here's how [examples/wire.p4app/main.py](examples/wire.p4app/main.py) looks:

```
from p4app import P4Mininet
from mininet.topo import SingleSwitchTopo

topo = SingleSwitchTopo(2)
net = P4Mininet(program='wire.p4', topo=topo)
net.start()

net.pingAll()

from mininet.cli import CLI
CLI(net)
```

This p4app script starts by importing P4Mininet, which is a p4app library that
extends Mininet with special functionality like compiling P4 programs and
configuring BMV2 switches. The script imports the `SingleSwitchTopo`
topology from Mininet. In this case the `topo` has two hosts connected to a
single switch. The Mininet network is instantiated by calling `P4Mininet`,
providing it with the program (`wire.p4`), as well as the topology it created
(`topo`). Once the network `net` is started, it can be used like a standard
Mininet network. Here the script tests connectivity by running Mininet's
`pingAll()`. Finally, the script launches the mininet CLI by calling `CLI(net)`.
This brings up a CLI that you can use to debug your network.

p4app and the Control Plane
===========================

Configuring Tables with P4Runtime
---------------------------------

Configuring tables in your P4 program is easy with p4app. P4app provides a
wrapper around P4Runtime to configure tables in your P4-16 program. You can
call `insertTableEntry()` on a switch object to add a table entry to that
switch. From [examples/ring.p4app](examples/ring.p4app/main.py):

```
sw.insertTableEntry(table_name='MyIngress.ipv4_lpm',
                    match_fields={'hdr.ipv4.dstAddr': ["10.0.0.%d" % i, 32]},
                    action_name='MyIngress.ipv4_forward',
                    action_params={'dstAddr': '00:00:00:00:00:%02x' % i,
                                      'port': 1})
```

You can also set a table's default action with `default_action=True`:

```
sw.insertTableEntry(table_name='MyIngress.ipv4_lpm',
                    default_action=True,
                    action_name='MyIngress.ipv4_forward',
                    action_params={'dstAddr': '00:00:00:00:00:00',
                                      'port': 2})
```

To inspect all the table entries for a switch, you can use:

```
sw.printTableEntries()
```


Multicast Groups
----------------

You can add multicast groups using `addMulticastGroup()`. From
[examples/multicast.p4app](examples/multicast.p4app/main.py):

```
sw.addMulticastGroup(mgid=mgid, ports=range(1, n+1))
```

Reading Counters
----------------

If your P4 program defines a counter, you can read it from the `main.py` script
while the switch is running using `readCounter()`. From
[examples/counter.p4app](examples/counter.p4app/main.py):

```
packet_count, byte_count = s1.readCounter('ingressPortCounter', port)
```

Configuring P4-14 Programs
--------------------------

If you are running a P4-14 program, there is no P4Runtime support, so you won't
be able to use the methods described above. Instead, you can use
`simple_switch_CLI` to configure the runtime of a P4-14 program. p4app provides
an interface to `simple_switch_CLI` through a `command()` method on each
switch. For example, to add a table entry to switch `s1`:

```
s1.command('table_add ipv4_lpm set_nhop 10.0.0.10/32 => 10.0.0.10 1')
```


Executing Commands Interactively
================================

To run commands interactively on a currently running p4app, you can use

```
p4app exec command arg1 arg2 ...
```

This will run a command in a currently running p4app instance. If there are
multiple instances running, the command will be executed on the most recently
started p4app.

To run a command on a Mininet host, you can use the Mininet `m` utility script,
which is included in p4app. For example, run `ping` on Mininet host `h1`:

```
p4app exec m h1 ping 10.0.0.2
```

Or, you can simply open a bash shell on one of the mininet hosts:
```
p4app exec m h1 bash
```

You can also run `tcpdump` on the Mininet host to see packets in realtime with
Wireshark:
```
p4app exec m h1 tcpdump -Uw - | wireshark -ki -
```

Advanced Features
=================

#### Custom Docker image

If you're hacking on the P4 toolchain or p4app itself, you may want to use a
modified Docker image instead of the standard p4lang one. That's easy to do;
just set the `P4APP_IMAGE` environment variable to the Docker image you'd like
to use. For example:

```
P4APP_IMAGE=me/my_p4app_image:latest p4app run my_program.p4app
```

#### Passing arguments to `main.py`

When you invoke p4app, you can pass extra arguments after the path to your
p4app directory. These arguments will be passed to the p4app `main.py` script.
For example, you can specify the number of switches for the `ring.p4app`
example:

```
~/p4app/p4app run examples/ring.p4app 4
```

The script parses these arguments using Python's `sys`:

```
import sys

if len(sys.argv) > 1:
    N = int(sys.argv[1])
```


#### Specify location of log directory
By default, p4app will mount the directory `/tmp/p4app-logs` on the host to
`/tmp/p4app-logs` on the docker container (guest). The output from bmv2, as well
as any output from your programs, will be saved to this directory.  Instead of
using the default directory (`/tmp/p4app-logs`), you can specify another
directory with the `$P4APP_LOGDIR` environment variable. For example, if you
run:

```
P4APP_LOGDIR=./out p4app run myapp.p4app
```

all the log files will be stored to `./out`.

