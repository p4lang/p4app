#include <core.p4>
#include <v1model.p4>
#include "includes/header.p4"
#include "includes/parser.p4"

control ingress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    register<bit<DATAPATH_SIZE>>(1) registerAcceptorID;
    register<bit<ROUND_SIZE>>(INSTANCE_COUNT) registerRound;
    register<bit<ROUND_SIZE>>(INSTANCE_COUNT) registerVRound;
    register<bit<VALUE_SIZE>>(INSTANCE_COUNT) registerValue;

    action read_round() {
        registerRound.read(meta.paxos_metadata.round, hdr.paxos.inst);
        meta.paxos_metadata.set_drop = 1;
    }

    table round_tbl {
        key = {}
        actions = {
            read_round;
        }
        size = 1;
        default_action = read_round;
    }

    action handle_1a() {
        hdr.paxos.msgtype = PAXOS_1B;
        registerVRound.read(hdr.paxos.vrnd, hdr.paxos.inst);
        registerValue.read(hdr.paxos.paxosval, hdr.paxos.inst);
        registerAcceptorID.read(hdr.paxos.acptid, 0);
        registerRound.write(hdr.paxos.inst, hdr.paxos.rnd);
        meta.paxos_metadata.set_drop = 0;

    }

    action handle_2a() {
        hdr.paxos.msgtype = PAXOS_2B;
        registerAcceptorID.read(hdr.paxos.acptid, 0);
        registerRound.write(hdr.paxos.inst, hdr.paxos.rnd);
        registerVRound.write(hdr.paxos.inst, hdr.paxos.rnd);
        registerValue.write(hdr.paxos.inst, hdr.paxos.paxosval);
        meta.paxos_metadata.set_drop = 0;
    }

    table acceptor_tbl {
        key = {hdr.paxos.msgtype : exact;}
        actions = {
            handle_1a;
            handle_2a;
            NoAction;
        }
        size = 4;
        default_action = NoAction;
    }

    action forward(PortId port) {
        standard_metadata.egress_spec = port;
        meta.paxos_metadata.set_drop = 0;
    }

    table forward_tbl {
        key = {meta.paxos_metadata.set_drop : exact; }
        actions = {
            forward;
            NoAction;
        }
        size = 2;
        default_action = NoAction();
    }

    apply {
        if (hdr.ipv4.isValid()) {
            if (hdr.paxos.isValid()) {
                round_tbl.apply();
                if (hdr.paxos.rnd >= meta.paxos_metadata.round) {
                    acceptor_tbl.apply();
                }
            }
            forward_tbl.apply();
        }
    }
}

control egress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {

    action _drop() {
        mark_to_drop(standard_metadata);
    }

    action set_UDPdstPort(bit<16> dstPort) {
        hdr.udp.dstPort = dstPort;
    }

    table transport_tbl {
        key = { meta.paxos_metadata.set_drop : exact; }
        actions = {
            _drop;
             set_UDPdstPort;
        }
        size = 2;
        default_action =  _drop();
    }

    apply {
        transport_tbl.apply();
    }
}

V1Switch(TopParser(), verifyChecksum(), ingress(), egress(), computeChecksum(), TopDeparser()) main;
