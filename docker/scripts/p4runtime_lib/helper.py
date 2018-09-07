# Copyright 2017-present Open Networking Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import re

import google.protobuf.text_format
from p4.v1 import p4runtime_pb2
from p4.config.v1 import p4info_pb2

from convert import encode

class ReplicaMgr(object):
    def __init__(self, group):
        self.group = group
    def append(self, port, rid):
        r = self.group.replicas.add()
        r.egress_port = port
        r.instance = rid
        return self
    def pop_back(self):
        del self.group.replicas[-1]
        return self
    # generator function to make ReplicaMgr iterable
    def __iter__(self):
        for r in self.group.replicas:
            yield (r.egress_port, r.instance)

class P4InfoHelper(object):
    def __init__(self, p4_info_filepath):
        p4info = p4info_pb2.P4Info()
        # Load the p4info file into a skeleton P4Info object
        with open(p4_info_filepath) as p4info_f:
            google.protobuf.text_format.Merge(p4info_f.read(), p4info)
        self.p4info = p4info

    def get(self, entity_type, name=None, id=None):
        if name is not None and id is not None:
            raise AssertionError("name or id must be None")

        for o in getattr(self.p4info, entity_type):
            pre = o.preamble
            if name:
                if (pre.name == name or pre.alias == name):
                    return o
            else:
                if pre.id == id:
                    return o

        if name:
            raise AttributeError("Could not find %r of type %s" % (name, entity_type))
        else:
            raise AttributeError("Could not find id %r of type %s" % (id, entity_type))

    def get_id(self, entity_type, name):
        return self.get(entity_type, name=name).preamble.id

    def get_name(self, entity_type, id):
        return self.get(entity_type, id=id).preamble.name

    def get_alias(self, entity_type, id):
        return self.get(entity_type, id=id).preamble.alias

    def __getattr__(self, attr):
        # Synthesize convenience functions for name to id lookups for top-level entities
        # e.g. get_tables_id(name_string) or get_actions_id(name_string)
        m = re.search("^get_(\w+)_id$", attr)
        if m:
            primitive = m.group(1)
            return lambda name: self.get_id(primitive, name)

        # Synthesize convenience functions for id to name lookups
        # e.g. get_tables_name(id) or get_actions_name(id)
        m = re.search("^get_(\w+)_name$", attr)
        if m:
            primitive = m.group(1)
            return lambda id: self.get_name(primitive, id)

        raise AttributeError("%r object has no attribute %r" % (self.__class__, attr))

    def get_match_field(self, table_name, name=None, id=None):
        for t in self.p4info.tables:
            pre = t.preamble
            if pre.name == table_name:
                for mf in t.match_fields:
                    if name is not None:
                        if mf.name == name:
                            return mf
                    elif id is not None:
                        if mf.id == id:
                            return mf
        raise AttributeError("%r has no attribute %r" % (table_name, name if name is not None else id))

    def get_match_field_id(self, table_name, match_field_name):
        return self.get_match_field(table_name, name=match_field_name).id

    def get_match_field_name(self, table_name, match_field_id):
        return self.get_match_field(table_name, id=match_field_id).name

    def get_match_field_pb(self, table_name, match_field_name, value):
        p4info_match = self.get_match_field(table_name, match_field_name)
        bitwidth = p4info_match.bitwidth
        p4runtime_match = p4runtime_pb2.FieldMatch()
        p4runtime_match.field_id = p4info_match.id
        match_type = p4info_match.match_type
        #print dir(p4info_pb2.MatchField)
        #if match_type == p4info_pb2.MatchField.VALID:
        if match_type == p4info_pb2.MatchField.IsInitialized:
            valid = p4runtime_match.valid
            valid.value = bool(value)
        elif match_type == p4info_pb2.MatchField.EXACT:
            exact = p4runtime_match.exact
            exact.value = encode(value, bitwidth)
        elif match_type == p4info_pb2.MatchField.LPM:
            lpm = p4runtime_match.lpm
            lpm.value = encode(value[0], bitwidth)
            lpm.prefix_len = value[1]
        elif match_type == p4info_pb2.MatchField.TERNARY:
            lpm = p4runtime_match.ternary
            lpm.value = encode(value[0], bitwidth)
            lpm.mask = encode(value[1], bitwidth)
        elif match_type == p4info_pb2.MatchField.RANGE:
            lpm = p4runtime_match.range
            lpm.low = encode(value[0], bitwidth)
            lpm.high = encode(value[1], bitwidth)
        else:
            raise Exception("Unsupported match type with type %r" % match_type)
        return p4runtime_match

    def get_match_field_value(self, match_field):
        match_type = match_field.WhichOneof("field_match_type")
        if match_type == 'valid':
            return match_field.valid.value
        elif match_type == 'exact':
            return match_field.exact.value
        elif match_type == 'lpm':
            return (match_field.lpm.value, match_field.lpm.prefix_len)
        elif match_type == 'ternary':
            return (match_field.ternary.value, match_field.ternary.mask)
        elif match_type == 'range':
            return (match_field.range.low, match_field.range.high)
        else:
            raise Exception("Unsupported match type with type %r" % match_type)

    def get_action_param(self, action_name, name=None, id=None):
        for a in self.p4info.actions:
            pre = a.preamble
            if pre.name == action_name:
                for p in a.params:
                    if name is not None:
                        if p.name == name:
                            return p
                    elif id is not None:
                        if p.id == id:
                            return p
        raise AttributeError("action %r has no param %r, (has: %r)" % (action_name, name if name is not None else id, a.params))

    def get_action_param_id(self, action_name, param_name):
        return self.get_action_param(action_name, name=param_name).id

    def get_action_param_name(self, action_name, param_id):
        return self.get_action_param(action_name, id=param_id).name

    def get_action_param_pb(self, action_name, param_name, value):
        p4info_param = self.get_action_param(action_name, param_name)
        p4runtime_param = p4runtime_pb2.Action.Param()
        p4runtime_param.param_id = p4info_param.id
        p4runtime_param.value = encode(value, p4info_param.bitwidth)
        return p4runtime_param

    def buildTableEntry(self,
                        table_name,
                        match_fields=None,
                        default_action=False,
                        action_name=None,
                        action_params=None,
                        priority=None):
        table_entry = p4runtime_pb2.TableEntry()
        table_entry.table_id = self.get_tables_id(table_name)

        if priority is not None:
            table_entry.priority = priority

        if match_fields:
            table_entry.match.extend([
                self.get_match_field_pb(table_name, match_field_name, value)
                for match_field_name, value in match_fields.iteritems()
            ])

        if default_action:
            table_entry.is_default_action = True

        if action_name:
            action = table_entry.action.action
            action.action_id = self.get_actions_id(action_name)
            if action_params:
                action.params.extend([
                    self.get_action_param_pb(action_name, field_name, value)
                    for field_name, value in action_params.iteritems()
                ])
        return table_entry

    def buildMulticastGroup(self,
                        mgid=None,
                        ports=None):
        group = p4runtime_pb2.MulticastGroupEntry()
        group.multicast_group_id = mgid
        replicas = ReplicaMgr(group)
        for i,port in enumerate(ports):
            replicas.append(port, i)
        return group

