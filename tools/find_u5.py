import sexpdata

with open('hardware/warden-apex-master/warden-apex-master.kicad_sch') as f:
    parsed = sexpdata.loads(f.read())

u5_pos = None
for item in parsed:
    if isinstance(item, list) and len(item) > 0 and item[0].value() == 'symbol':
        is_ref = False
        at = None
        for sub in item:
            if isinstance(sub, list) and len(sub) > 0:
                if sub[0].value() == 'property' and sub[1] == 'Reference' and sub[2] == 'U5':
                    is_ref = True
                if sub[0].value() == 'at':
                    at = sub
        if is_ref and at:
            u5_pos = (float(at[1]), float(at[2]))
            print("U5 pos:", u5_pos)
