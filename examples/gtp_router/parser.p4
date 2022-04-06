parser ParserImpl(packet_in packet, out headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    @name("parse_ethernet") state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            16w0x800: parse_ipv4;
            default: accept;
        }
    }
    @name("parse_ipv4") state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition accept;
    }
    @name("parse_udp") state parse_udp {
        packet.extract(hdr.udp);
        transition select(hdr.udp.dstPort) {
            2152: parse_gtp;
            default: accept;
        }
    }
    @name("parse_gtp") state parse_gtp {
        packet.extract(hdr.gtp_common);
        transition select(hdr.gtp_common.version) {
            1 : parse_teid;
            2 : parse_gtpv2;
            default: accept;
        }
    }
    @name("parse_teid") state parse_teid {
        packet.extract(hdr.gtp_teid);
        transition parse_inner;
    }
    @name("parse_gtpv2") state parse_gtpv2 {
        packet.extract(hdr.gtpv2_ending);
        transition accept;
    }
    @name("parse_gtpv1optional") state parse_gtpv1optional {
        packet.extract(hdr.gtpv1_optional);
        transition parse_inner;
    }
    @name("parse_inner") state parse_inner {
        packet.extract(hdr.inner_ipv4);
        transition accept;
    }
    @name("start") state start {
        transition parse_ethernet;
    }
}

control DeparserImpl(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.udp);
        packet.emit(hdr.gtp_common);
        packet.emit(hdr.gtp_teid);
        packet.emit(hdr.inner_ipv4);
        packet.emit(hdr.inner_udp);
        packet.emit(hdr.inner_tcp);
    }
}

control verifyChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

control computeChecksum(inout headers hdr, inout metadata meta) {
    apply {
        update_checksum(
                hdr.ipv4.isValid(),
                { hdr.ipv4.version, hdr.ipv4.ihl, hdr.ipv4.diffserv,
                hdr.ipv4.totalLen, hdr.ipv4.identification,
                hdr.ipv4.flags, hdr.ipv4.fragOffset, hdr.ipv4.ttl,
                hdr.ipv4.protocol, hdr.ipv4.srcAddr, hdr.ipv4.dstAddr },
                hdr.ipv4.hdrChecksum,
                HashAlgorithm.csum16);
    }
}

