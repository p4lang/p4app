#ifndef __HEADER_P4__
#define __HEADER_P4__ 1

const bit<8>  IPPROTO_UDP  = 0x11;
const bit<16> GTP_UDP_PORT = 2152;
const bit<48> ENS6_MAC     = 0x02af609d6a36;
const bit<48> ETH0_FTP_MAC = 0x0215bcff37b0;


struct ingress_metadata_t {
    bit<32> nhop_ipv4;
}

header ethernet_t {
    bit<48> dstAddr;
    bit<48> srcAddr;
    bit<16> etherType;
}

header ipv4_t {
    bit<4>  version;
    bit<4>  ihl;
    bit<8>  diffserv;
    bit<16> totalLen;
    bit<16> identification;
    bit<3>  flags;
    bit<13> fragOffset;
    bit<8>  ttl;
    bit<8>  protocol;
    bit<16> hdrChecksum;
    bit<32> srcAddr;
    bit<32> dstAddr;
}

header gtp_common_t {
    bit<3> version; /* this should be 1 for GTPv1 and 2 for GTPv2 */
    bit<1> pFlag;   /* protocolType for GTPv1 and pFlag for GTPv2 */
    bit<1> tFlag;   /* only used by GTPv2 - teid flag */
    bit<1> eFlag;   /* only used by GTPv1 - E flag */
    bit<1> sFlag;   /* only used by GTPv1 - S flag */
    bit<1> pnFlag;  /* only used by GTPv1 - PN flag */
    bit<8> messageType;
    bit<16> messageLength;
}
header gtp_teid_t {
    bit<32> teid;
}

/* GPRS Tunnelling Protocol (GTP) v1 */

/*
This header part exists if any of the E, S, or PN flags are on.
*/
header gtpv1_optional_t {
    bit<16> sNumber;
    bit<8> pnNumber;
    bit<8> nextExtHdrType;
}

/* Extension header if E flag is on. */

header gtpv1_extension_hdr_t {
    bit<8> plength; /* length in 4-octet units */
    varbit<128> contents;
    bit<8> nextExtHdrType;
}


/* GPRS Tunnelling Protocol (GTP) v2 (also known as evolved-GTP or eGTP) */
header gtpv2_ending_t {
    bit<24> sNumber;
    bit<8> reserved;
}

header udp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<16> plength;
    bit<16> checksum;
}
header tcp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  dataOffset;
    bit<4>  res;
    bit<8>  flags;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}

struct metadata {
    @name("ingress_metadata")
    ingress_metadata_t   ingress_metadata;
}

struct headers {
    @name("ethernet")
    ethernet_t ethernet;
    @name("ipv4")
    ipv4_t  ipv4;
    @name("udp")
    udp_t udp;
    @name("gtp_common")
    gtp_common_t gtp_common;
    @name("gtp_teid")
    gtp_teid_t  gtp_teid;
    @name("gtpv2_ending")
    gtpv2_ending_t gtpv2_ending;
    @name("gtpv1_optional")
    gtpv1_optional_t gtpv1_optional;
    @name("inner_ipv4")
    ipv4_t  inner_ipv4;
    @name("inner_udp")
    udp_t  inner_udp;
    @name("inner_tcp")
    tcp_t  inner_tcp;
}

error {
    IPv4IncorrectVersion,
    IPv4OptionsNotSupported
}

#endif // __HEADER_P4__
