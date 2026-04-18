import sexpdata

sch_file = 'hardware/warden-apex-master/warden-apex-master.kicad_sch'
with open(sch_file, 'r') as f:
    parsed = sexpdata.loads(f.read())

for item in parsed:
    if isinstance(item, list) and len(item) > 0 and item[0].value() == 'label':
        # print labels near U1 (203.2 - 12.7 = 190.5, Y around 152.4)
        try:
            for sub in item:
                if isinstance(sub, list) and sub[0].value() == 'at':
                    x, y = float(sub[1]), float(sub[2])
                    if 180 < x < 230 and 130 < y < 170:
                        print("Label", item[1], "at", x, y)
        except Exception:
            pass
