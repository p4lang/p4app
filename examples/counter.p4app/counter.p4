/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

const bit<32> MAX_PORTS = 128;


struct metadata { }

struct headers { }

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {
    state start { transition accept; }
}

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    counter(MAX_PORTS, CounterType.packets_and_bytes) ingressPortCounter;
    direct_counter(CounterType.packets_and_bytes) egressPortDirectCounter;

    action count_egress_spec () {
        egressPortDirectCounter.count();
    }

    table egress_port_stats_counting_table {
        key = {
            standard_metadata.egress_spec :  exact;
        }
        actions = {
            count_egress_spec;
            NoAction;
        }
        counters = egressPortDirectCounter;
        size = 64;
        default_action = NoAction;
    }

    apply {

        ingressPortCounter.count((bit<32>) standard_metadata.ingress_port);

        if (standard_metadata.ingress_port == 1)
            standard_metadata.egress_spec = 2;
        else
            standard_metadata.egress_spec = 1;

        egress_port_stats_counting_table.apply();
    }
}

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply { }
}

control MyComputeChecksum(inout headers  hdr, inout metadata meta) {
     apply { }
}

control MyDeparser(packet_out packet, in headers hdr) {
    apply { }
}

V1Switch(
MyParser(),
MyVerifyChecksum(),
MyIngress(),
MyEgress(),
MyComputeChecksum(),
MyDeparser()
) main;
