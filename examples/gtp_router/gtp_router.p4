#include <core.p4>
#include <v1model.p4>

#include "header.p4"
#include "parser.p4"

control ingress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata)
{
    bool dropped = false;

    action drop_action() {
        mark_to_drop(standard_metadata);
        dropped = true;
    }

    action to_port_action(bit<9> port) {
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
        standard_metadata.egress_spec = port;
    }

    action gtp_decapsulate(bit<9> port) {
        hdr.ipv4 = hdr.inner_ipv4;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
        hdr.ethernet.srcAddr = ENS6_MAC;
        hdr.ethernet.dstAddr = ETH0_FTP_MAC;
        standard_metadata.egress_spec = port;
        hdr.udp.setInvalid();
        hdr.gtp_common.setInvalid();
        hdr.gtp_teid.setInvalid();
        hdr.inner_ipv4.setInvalid();
    }
    action gtp_encapsulate(bit<9>  port) {
        standard_metadata.egress_spec = port;
        hdr.inner_ipv4.setValid();
        hdr.inner_ipv4 = hdr.ipv4;
        hdr.inner_udp = hdr.udp;
        hdr.udp.setValid();
        hdr.gtp_common.setValid();
        hdr.gtp_teid.setValid();
        hdr.udp.srcPort = GTP_UDP_PORT;
        hdr.udp.dstPort = GTP_UDP_PORT;
        hdr.udp.checksum = 0;
        hdr.udp.plength = hdr.ipv4.totalLen + 8;
        hdr.gtp_teid.teid = 0x4500003c;
        hdr.gtp_common.version = 1;
        hdr.gtp_common.pFlag = 1;
        hdr.gtp_common.messageType = 255;
        hdr.gtp_common.messageLength = hdr.ipv4.totalLen + 8;
        hdr.ipv4.srcAddr = 0xc0a8fa02; //192.168.250.2
        hdr.ipv4.dstAddr = 0xac1e2719; // 172.30.39.25
        hdr.ipv4.protocol = IPPROTO_UDP;
        hdr.ipv4.ttl = 255;
        hdr.ipv4.totalLen = hdr.udp.plength + 28;
    }

    table ipv4_match {
        key = {
            hdr.gtp_teid.teid: exact;
        }
        actions = {
            to_port_action;

        }
        size = 1024;
    }
   table ipv4_match_encap {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            gtp_encapsulate;

        }
        size = 1024;
    }

    apply {
        ipv4_match.apply();
        ipv4_match_encap.apply();
        if (dropped) return;
    }
}

control egress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    apply { }
}


V1Switch(ParserImpl(), verifyChecksum(), ingress(), egress(), computeChecksum(), DeparserImpl()) main;
