import re
try:
    with open('/usr/share/kicad/symbols/Logic_LevelTranslator.kicad_sym') as f:
        lib = f.read()
    if 'TXS0102DCU' in lib:
        print("TXS0102DCU found")
    elif 'TXB0102DCU' in lib:
        print("TXB0102DCU found")
    else:
        print("Not found")
except Exception as e:
    print(e)
