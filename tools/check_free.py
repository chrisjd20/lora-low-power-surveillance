import sexpdata

sch_file = 'hardware/warden-apex-master/warden-apex-master.kicad_sch'
with open(sch_file, 'r') as f:
    parsed = sexpdata.loads(f.read())

for item in parsed:
    if isinstance(item, list) and len(item) > 0 and item[0].value() == 'label':
        try:
            for sub in item:
                if isinstance(sub, list) and sub[0].value() == 'at':
                    x, y = float(sub[1]), float(sub[2])
                    if 180 < x < 230 and 130 < y < 170:
                        pass
        except Exception:
            pass

# Which pins of U1 are free?
u1_y = 152.4
u1_x = 203.2
xiao_lib = [
    (1, -12.7, 13.97), (2, -12.7, 11.43), (3, -12.7, 8.89), (4, -12.7, 6.35),
    (5, -12.7, 3.81), (6, -12.7, 1.27), (7, -12.7, -1.27), (8, -12.7, -3.81),
    (9, -12.7, -6.35), (10, -12.7, -8.89), (11, -12.7, -11.43), (12, -12.7, -13.97),
    (13, 12.7, 13.97), (14, 12.7, 11.43), (15, 12.7, 8.89), (16, 12.7, 6.35),
    (17, 12.7, 3.81), (18, 12.7, 1.27), (19, 12.7, -1.27), (20, 12.7, -3.81),
    (21, 12.7, -6.35), (22, 12.7, -8.89), (23, 12.7, -11.43), (24, 12.7, -13.97)
]

labels_found = set()
for item in parsed:
    if isinstance(item, list) and len(item) > 0 and item[0].value() == 'label':
        name = item[1]
        for sub in item:
            if isinstance(sub, list) and sub[0].value() == 'at':
                x, y = float(sub[1]), float(sub[2])
                # Check distance to each pin
                for p_num, p_x, p_y in xiao_lib:
                    abs_x = u1_x + p_x
                    abs_y = u1_y - p_y
                    if abs(x - abs_x) < 0.1 and abs(y - abs_y) < 0.1:
                        labels_found.add(p_num)

for p_num, p_x, p_y in xiao_lib:
    if p_num not in labels_found:
        print(f"Pin {p_num} is free")
