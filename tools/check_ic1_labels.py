import sexpdata

with open('hardware/warden-apex-master/warden-apex-master.kicad_sch') as f:
    parsed = sexpdata.loads(f.read())

for item in parsed:
    if isinstance(item, list) and len(item) > 0 and item[0].value() == 'label':
        for sub in item:
            if isinstance(sub, list) and len(sub) > 0 and sub[0].value() == 'at':
                x, y = float(sub[1]), float(sub[2])
                # IC1 is at X=101.6, Y=254.0.
                # Pin 1: (12.7, 46.99, 180.0) -> X = 101.6 - 12.7 = 88.9, Y = 254.0 - (-46.99)? wait. rotation 180!
                # Wait! IC1 has rotation 0. So Pin 1 at 180 means it points left. X=12.7 means X_pos + 12.7 = 114.3. Y = 254.0 - 46.99 = 207.01.
                # Let's just find any labels near IC1 (101.6 +/- 20, 254.0 +/- 50)
                if 80 < x < 120 and 200 < y < 300:
                    print("Label", item[1], "at", x, y)
