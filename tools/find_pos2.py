import sexpdata
import sys
import math

sch_file = 'hardware/warden-apex-master/warden-apex-master.kicad_sch'
with open(sch_file, 'r') as f:
    content = f.read()

parsed = sexpdata.loads(content)

def find_symbol_pos(ref):
    for item in parsed:
        if isinstance(item, list) and len(item) > 0 and item[0].value() == 'symbol':
            is_ref = False
            at = None
            for sub in item:
                if isinstance(sub, list) and len(sub) > 0:
                    if sub[0].value() == 'property' and sub[1] == 'Reference' and sub[2] == ref:
                        is_ref = True
                    if sub[0].value() == 'at':
                        at = sub
            if is_ref and at:
                return float(at[1]), float(at[2]), float(at[3]) if len(at)>3 else 0.0
    return None

ic1_pos = find_symbol_pos('IC1')
u1_pos = find_symbol_pos('U1')

print(f"IC1 pos: {ic1_pos}")
print(f"U1 pos: {u1_pos}")
