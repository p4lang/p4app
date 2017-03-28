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
supporting files, and a `p4app.json` file that tells p4app how to run it.

This repository comes with an example p4app called `simple_router.p4app`. Here's
how you can run it:

```
p4app run examples/simple_router.p4app
```

If you run this command, you'll find yourself at a Mininet command prompt. p4app
will automatically download a Docker image containing the P4 compiler and tools,
compile `simpler_router.p4`, and set up a container with a simulated network you
can use to experiment. In addition to Mininet itself, you can use `tshark`,
`scapy`, and the net-tools and nmap suites right out of the box.

Mininet isn't the only backend that p4app supports, though. Here's another
example p4app:

```
p4app run examples/simple_counter.p4app
```

If you run this command, p4app will automatically compile `simple_counter.p4`,
feed it a sequence of input packets defined in `simple_counter.stf`, and make
sure it gets the output packets it expects. This example uses the "simple
testing framework", which can help you test small P4 programs and ensure they
behave the way you expect.

A p4app package contains one program, but it can contain multiple "targets" -
for example, a p4app might include several different network configurations for
Mininet, an entire suite of STF tests, or a mix of the two. p4app runs the
default target, well, by default, but you can specify a target by name this way:

```
p4app run examples/simple_router.p4app mininet
```

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
    |- p4app.json
    |
    |- my_program.p4
    |
    |- ...other files...
```

The `p4app.json` file is a package manifest that tells p4app how to build and
run a P4 program; it's comparable to a Makefile. Here's one looks:

```
{
  "program": "my_program.p4",
  "language": "p4-14",
  "targets": {
    "mininet": {
      "num-hosts": 2,
      "switch-config": "my_program.config"
    }
  }
}
```

This manifest tells p4app that it should run `my_program.p4`, which is written
in `p4-14` - that's the current version of the P4 language, though you can also
use `p4-16` to use the P4-16 draft revision. It defines one target, `mininet`,
and it provides some Mininet configuration options: there will be two hosts on
the network, and the simulated switch will be configured using the file
`my_program.config`. When you reference an external file in `p4app.json` like
this, just place that file in the package, and p4app will make sure that the
appropriate tools can find it.

If there are multiple targets and the user doesn't specify one by name, p4app
will run one of the targets, chosen arbitrarily. You can set the default target
to be run using the `default-target` option. Here's an example with several
targets:

```
{
  "program": "my_program.p4",
  "language": "p4-14",
  "default-target": "debug",
  "targets": {
    "debug": { "use": "mininet", "num-hosts": 2 },
    "test1": { "use": "stf", "test": "test1.stf" },
    "test2": { "use": "stf", "test": "test2.stf" },
  }
}
```

This defines one Mininet target, "debug", and two STF targets, "test1" and
"test2". The `use` field specifies which backend a target uses; if you don't
provide it, the target name is also used as the backend name. That's why, in
the previous example, we didn't have to specify `"use": "mininet"` - the
target's name is mininet, and that's enough for p4app to know what you mean.

That's really all there is to it. There's one final tip: if you want to share a
p4app package with someone else, you can run `p4app pack my-program.p4app`, and
p4app will compress the package into a single file. p4app can run compressed
packages transparently, so the person you send it to won't even have to
decompress it. If they want to take a look at the files it contains, though,
they can just run `p4app unpack my-program.p4app`, and p4app will turn the
package back into a directory.

Backends
========

mininet
-------

This backend compiles a P4 program, loads it into a BMV2
[simple_switch](https://github.com/p4lang/behavioral-model/blob/master/docs/simple_switch.md),
and creates a Mininet environment that lets you experiment with it.

The following configuration values are supported:

```
"mininet": {
  "num-hosts": 2,
  "switch-config": "file.config"
}
```

All are optional.

The Mininet network will use a star topology, with `num-hosts` hosts each
connected to your switch via a separate interface.

You can load a configuration into your switch at startup using `switch-config`;
the file format is just a sequence of commands for the BMV2
[simple_switch_CLI](https://github.com/p4lang/behavioral-model#using-the-cli-to-populate-tables).

During startup, messages will be displayed telling you information about the
network configuration and about how to access logging and debugging facilities.
The BMV2 debugger is especially handy; you can read up on how to use it
[here](https://github.com/p4lang/behavioral-model/blob/master/docs/p4dbg_user_guide.md).

This target also supports the configuration values for the `compile-bvm2` target.

multiswitch
-----------

Like `mininet`, this target compiles a P4 program and runs it in a Mininet
environment. Moreover, this target allows you to run multiple switches with a
custom topology and execute arbitrary commands on the hosts. The switches are
automatically configured with l2 and l3 rules for routing traffic to all hosts
(this assumes that the P4 programs have the `ipv4_lpm`, `send_frame` and
`forward` tables). For example:

```
"multiswitch": {
  "links": [
    ["h1", "s1"],
    ["s1", "s2"],
    ["s2", "h2", 50]
  ],
  "hosts": {
    "h1": {
      "cmd": "python echo_server.py %port%",
      "startup_sleep": 0.2,
      "wait": false
    },
    "h2": {
      "cmd": "python echo_client.py h1 %port% %echo_msg%",
      "wait": true
    }
  },
  "parameters": {
    "port": 8000,
    "echo_msg": "foobar"
  }
}
```

This configuration will create a topology like this:

```
h1 <---> s1 <---> s2 <---> h2
```

where the `s2-h2` link has a 50ms artificial delay. The hosts can be configured
with the following options:

 - `cmd` - the command to be executed on the host.
 - `wait` - wait for the command to complete before continuing. By setting it
   to false, you can start a process on the host in the background, like a
   daemon/server.
 - `startup_sleep` - the amount of time (in seconds) that should be waited
   after starting the command.
 - `latency` - the latency between this host and the switch. This can either be a number (interpreted as seconds) or a string with time units (e.g. `50ms` or `1s`). This overrides the latency set in the `links` object.

The command is formatted by replacing the hostnames (e.g. `h1`) with the
corresponding IP address, and the parameters (surrounded by '%', e.g.
`%port%`) with their corresponding values. The parameters should be defined in
the multiswitch target in the manifest. For example, have a look at the
[manifest](examples/multiswitch.p4app/p4app.json) for the multiswitch example
app.

#### Limitations
Currently, each host can be connected to at most one switch.


#### Specifying entries for each switch
The routing tables (`ipv4_lpm`, `send_frame` and `forward`) are automatically
populated with this target. Additionally, you can specify custom entries to be
added to each switch. You can either include a commands file, or an array of
entries. These custom entries will have precedence over the automatically
generated ones for the routing tables. For example:

```
"multiswitch": {
  "links": [ ... ],
  "hosts": { ... },
  "switches": {
    "s1": {
      "entries": "s1_commands.txt"
    },
    "s2": {
      "entries": [
        "table_add ipv4_lpm set_nhop 10.0.1.10/32 => 10.0.1.10 1",
        "table_add ipv4_lpm set_nhop 10.0.2.10/32 => 10.0.2.10 2"
      ]
    }
  }
}
```

If the entries for `s2` above overlap with the automatically generated entries
(e.g. there is an automatic entry for `set_nhop 10.0.1.10/32`), these custom
entries will have precedence and you will see a warning about a duplicate entry
while the tables are being populated.

#### Logging
When this target is run, a temporary directory on the host, `/tmp/p4app_log`,
is mounted on the guest at `/tmp/p4app_log`. All data in this directory is
persisted to the host after running the p4app. The stdout from the hosts'
commands is stored in this location. If you need to save the output (e.g. logs)
of a command, you can also put that in this directory.

To save the debug logs from the P4 switches, set `"bmv2_log": true` in the
target. To capture PCAPs from all switches, set `"pcap_dump": true`. These
files will be saved to `/tmp/p4app_log`. For example usage, see the
[manifest](examples/broadcast.p4app/p4app.json) for the broadcast example app.

#### Cleanup commands
If you need to execute commands in the docker container after running the
target (and before mininet is stopped), you can use `after`. `after` should
contain `cmd`, which can either be a command or a list of commands. For
example:

```
"multiswitch": {
  "links": [ ... ],
  "hosts": { ... },
  "after": {
    "cmd": [
      "echo register_read my_register 1 | simple_switch_CLI --json p4src/my_router.p4.json",
      "echo register_read my_register 2 | simple_switch_CLI --json p4src/my_router.p4.json"
    ]
  }
}
```

custom
-----------

This is a third method for compiling a P4 program to run in a Mininet
environment. This target allows you to specify a Python `program` that
uses Mininet's Python API to specify the network topology and configuration.
For example:

```
{
  "program": "source_routing.p4",
  "language": "p4-14",
  "targets": {
      "custom": {
	       "program": "topo.py"
      }
  }
}

```

This target will invoke the python script `topo.py` to start Mininet.

stf
---

This target compiles the provided P4 program and run a test against it written
for the STF testing framework.

There is one configuration value, which is required:

```
"stf": {
  "test": "file.stf"
}
```

You must write the file specified by `test` in the STF format, which is
unfortunately currently undocumented. (If you'd like to reverse engineer it and
provide some documentation, please submit a PR!) You can take a look at the
example p4apps included in this repo to get a sense of the basics.

This target also supports the configuration values for the `compile-bvm2` target.

compile-bmv2
------------

This is a simple backend that just attempts to compile the provided P4 program
for the BMV2 architecture.

The following optional configuration values are supported:

```
"compile-bmv2": {
  "compiler-flags": ["-v", "-E"],
  "run-before-compile": ["date"],
  "run-after-compile": ["date"]
}
```

Advanced Features
=================

If you're hacking on the P4 toolchain or p4app itself, you may want to use a
modified Docker image instead of the standard p4lang one. That's easy to do;
just set the `P4APP_IMAGE` environment variable to the Docker image you'd like
to use. For example:

```
P4APP_IMAGE=me/my_p4app_image:latest p4app run examples/simple_router.p4app
```

#### Specify the name of the manifest file
By default, p4app will use the manifest file called `p4app.json` in the app's
directory. If your manifest file is not called `p4app.json`, you can use the
`--manifest` option to specify the name of the manifest. For example:

```
p4app run myapp.p4app --manifest testing.p4app
```
