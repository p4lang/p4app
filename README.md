p4app
=====

p4app is a tool that that can build, run, debug, and test P4 programs.
The philosophy behind p4app is "easy things should be easy" - p4app is designed
to make small, simple P4 programs easy to write and easy to share with others.

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
compile `simpler_router.p4`, and set up a container with a simulated network
you can use to experiment. In addition to Mininet itself, you can use `tshark`
and the net-tools and nmap suites right out of the box.

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
will run the first target in the list. Here's an example with several targets:

```
{
  "program": "my_program.p4",
  "language": "p4-14",
  "targets": {
    "debug": { "use": "mininet", "num-hosts": 2 },
    "test1": { "use": "stf", "test": "test1.stf" },
    "test2": { "use": "stf", "test": "test2.stf" },
  }
}
```

This defines one Mininet target and two STF targets. The `use` field specifies
which backend a target uses; if you don't provide it, the default is to use the
backend with the same name as the name of the target. That's why, in the
previous example, we didn't have to specify `"use": "mininet"` - the target's
name is mininet, and that's enough for p4app to know what you mean.

That's really all there is to it. There's one final tip: if you want to share a
p4app package with someone else, you can just tar and gzip the whole directory.
p4app can work transparently with compressed packages - just give it a `.p4app`
extension, and everything will work.

Backends
========

mininet
-------

This backend compiles a P4 program, loads it into a BMV2
[simple_switch](https://github.com/p4lang/behavioral-model/blob/master/docs/simple_switch.md),
and creates a Mininet environment that lets you experiment with it.

The following optional configuration values are supported:

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
