import sexpdata

with open('hardware/warden-apex-master/warden-apex-master.kicad_sch') as f:
    parsed = sexpdata.loads(f.read())

q3_sexp = None
r1_sexp = None
for item in parsed:
    if isinstance(item, list) and len(item) > 0 and item[0].value() == 'symbol':
        for sub in item:
            if isinstance(sub, list) and len(sub) > 0 and sub[0].value() == 'property' and sub[1] == 'Reference':
                if sub[2] == 'Q3':
                    q3_sexp = item
                if sub[2] == 'R1':
                    r1_sexp = item

print("Q3 found:", q3_sexp is not None)
print("R1 found:", r1_sexp is not None)

# Dump to strings
if q3_sexp:
    with open('tools/q3_dump.txt', 'w') as f:
        f.write(sexpdata.dumps(q3_sexp))
if r1_sexp:
    with open('tools/r1_dump.txt', 'w') as f:
        f.write(sexpdata.dumps(r1_sexp))
