/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

const bit<16> TYPE_IPV4    = 0x800;
const bit<8>  IP_PROT_UDP  = 0x11;

const bit<8>  OP_READ_REG  = 0x1;
const bit<8>  OP_WRITE_REG = 0x2;
const bit<16> UDP_PORT     = 1234;

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;

header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    bit<8>    diffserv;
    bit<16>   totalLen;
    bit<16>   identification;
    bit<3>    flags;
    bit<13>   fragOffset;
    bit<8>    ttl;
    bit<8>    protocol;
    bit<16>   hdrChecksum;
    ip4Addr_t srcAddr;
    ip4Addr_t dstAddr;
}

header udp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<16> length_;
    bit<16> checksum;
}

header myHdr_t {
    bit<8>  opType;
    bit<8>  idx;
    bit<32> val;
}

struct metadata { }

struct headers {
    ethernet_t        ethernet;
    ipv4_t            ipv4;
    udp_t             udp;
    myHdr_t           myHdr;
}

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {
    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }

    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            IP_PROT_UDP: parse_udp;
            default: accept;
        }
    }

    state parse_udp {
        packet.extract(hdr.udp);
        transition select(hdr.udp.dstPort) {
            UDP_PORT: parse_myHdr;
            default : accept;
        }
    }

    state parse_myHdr {
        packet.extract(hdr.myHdr);
        transition accept;
    }
}

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    register<bit<32>>(128) myReg;

    action reply() {
        standard_metadata.egress_spec = standard_metadata.ingress_port;

        macAddr_t tmpDstMac = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = hdr.ethernet.srcAddr;
        hdr.ethernet.srcAddr = tmpDstMac;

        ip4Addr_t tmpDstIp = hdr.ipv4.dstAddr;
        hdr.ipv4.dstAddr = hdr.ipv4.srcAddr;
        hdr.ipv4.srcAddr = tmpDstIp;

        bit<16> tmpDstPort = hdr.udp.dstPort;
        hdr.udp.dstPort = hdr.udp.srcPort;
        hdr.udp.srcPort = tmpDstPort;
        hdr.udp.checksum = 0;

    }


    apply {

        if (hdr.myHdr.isValid()) {
            if (hdr.myHdr.opType == OP_READ_REG) {
                myReg.read(hdr.myHdr.val, (bit<32>)hdr.myHdr.idx);
            }
            else if (hdr.myHdr.opType == OP_WRITE_REG) {
                myReg.write((bit<32>)hdr.myHdr.idx, hdr.myHdr.val);
            }
        }

        reply();

    }
}

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply { }
}

control MyComputeChecksum(inout headers  hdr, inout metadata meta) {
     apply {
	update_checksum(
	    hdr.ipv4.isValid(),
            { hdr.ipv4.version,
	      hdr.ipv4.ihl,
              hdr.ipv4.diffserv,
              hdr.ipv4.totalLen,
              hdr.ipv4.identification,
              hdr.ipv4.flags,
              hdr.ipv4.fragOffset,
              hdr.ipv4.ttl,
              hdr.ipv4.protocol,
              hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16);
    }
}

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.udp);
        packet.emit(hdr.myHdr);
    }
}

V1Switch(
MyParser(),
MyVerifyChecksum(),
MyIngress(),
MyEgress(),
MyComputeChecksum(),
MyDeparser()
) main;
