import sexpdata
import sys

with open('hardware/warden-apex-master/warden-apex-master.kicad_sch') as f:
    parsed = sexpdata.loads(f.read())

for item in parsed:
    if isinstance(item, list) and len(item) > 0 and item[0].value() == 'lib_symbols':
        for sym in item[1:]:
            if isinstance(sym, list) and len(sym) > 0 and sym[0].value() == 'symbol':
                if 'SRV05-4' in sym[1]:
                    # This is the symbol
                    for part in sym:
                        if isinstance(part, list) and part[0].value() == 'symbol':
                            for obj in part:
                                if isinstance(obj, list) and obj[0].value() == 'pin':
                                    num = None
                                    at = None
                                    for prop in obj:
                                        if isinstance(prop, list) and prop[0].value() == 'number':
                                            num = prop[1]
                                        if isinstance(prop, list) and prop[0].value() == 'at':
                                            at = prop
                                    if num and at:
                                        print(f"Pin {num} at {at[1]} {at[2]}")
