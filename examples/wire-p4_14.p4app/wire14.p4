parser start {
    return ingress;
}

action a1 () { modify_field(standard_metadata.egress_spec, 2); }
table t1 { actions { a1; } default_action: a1; }

action a2 () { modify_field(standard_metadata.egress_spec, 1); }
table t2 { actions { a2; } default_action: a2; }

control ingress {
        if (standard_metadata.ingress_port == 1)
            apply(t1);
        else
            apply(t2);
}
