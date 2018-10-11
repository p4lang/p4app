parser start {
    return ingress;
}

action a1(port) {
    modify_field(standard_metadata.egress_spec, port);
}

table t1 {
    actions { a1; }
}

control ingress {
    apply(t1);
}
