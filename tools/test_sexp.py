import sexpdata
import sys

sch_file = 'hardware/warden-apex-master/warden-apex-master.kicad_sch'
with open(sch_file, 'r') as f:
    content = f.read()
    
# check if we can parse and dump it without breaking it
try:
    parsed = sexpdata.loads(content)
    print("Parsed successfully. Length:", len(parsed))
except Exception as e:
    print("Error parsing:", e)
