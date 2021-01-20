from p4app import P4Program
import json

# Compile a P4_16 program:
prog16 = P4Program('wire.p4')
prog16.compile()

# Inspect the compiled JSON file
with open(prog16.json(), 'r') as f:
    bmv2_json = json.load(f)
    #print bmv2_json['actions']


# Compile a P4_14 program:
prog14 = P4Program('wire14.p4', version=14)
prog14.compile()

with open(prog14.json(), 'r') as f:
    bmv2_json = json.load(f)


print("OK")
