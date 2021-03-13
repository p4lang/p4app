# Implementing a P4 Switch based on PSA

Run this app.

```bash
p4app run examples/simple_switch_psa.p4app
```

Start capture on h2 from another shell.

```bash
p4app exec m h2 tcpdump
```

Send packet from h1 whose length was large than 100 bytes.

```
mininet> h1 python send.py 
###[ Ethernet ]###
  dst       = 00:04:00:00:00:01
  src       = 00:00:00:00:00:00
  type      = 0x1234
###[ Raw ]###
     load      = 'girl drives odd foolishly. girl runs stupid crazily. girl runs clueless foolishly. puppy runs stupid crazily. '
.
Sent 1 packets.
```

See captured packet and find that the packet was truncated to 64 bytes.

```bash
$ p4app exec m h2 tcpdump
tcpdump: verbose output suppressed, use -v or -vv for full protocol decode
listening on h2-eth0, link-type EN10MB (Ethernet), capture size 262144 bytes
14:51:48.709887 00:00:00:00:00:00 (oui Ethernet) > 00:04:00:00:00:01 (oui Unknown), ethertype Unknown (0x1234), length 124: 
        0x0000:  6769 726c 2064 7269 7665 7320 6f64 6420  girl.drives.odd.
        0x0010:  666f 6f6c 6973 686c 792e 2067 6972 6c20  foolishly..girl.
        0x0020:  7275 6e73 2073 7475 7069 6420 6372 617a  runs.stupid.craz
        0x0030:  696c 792e 2067 6972 6c20 7275 6e73 2063  ily..girl.runs.c
        0x0040:  6c75 656c 6573 7320 666f 6f6c 6973 686c  lueless.foolishl
        0x0050:  792e 2070 7570 7079 2072 756e 7320 7374  y..puppy.runs.st
        0x0060:  7570 6964 2063 7261 7a69 6c79 2e20       upid.crazily..
```
