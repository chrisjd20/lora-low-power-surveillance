import re

with open('hardware/warden-apex-master/warden-apex-master.kicad_sch', 'r') as f:
    sch = f.read()

# Label UART1_RX at 114.3 207.01
sch = sch.replace(
    '(label "UART1_RX" (at 114.3 207.01 0)',
    '(label "UART1_TX_1V8" (at 114.3 207.01 0)'
)

# Label UART1_TX at 88.9 289.56
sch = sch.replace(
    '(label "UART1_TX" (at 88.9 289.56 0)',
    '(label "UART1_RX_1V8" (at 88.9 289.56 0)'
)

with open('hardware/warden-apex-master/warden-apex-master.kicad_sch', 'w') as f:
    f.write(sch)

print("Replaced UART labels near IC1.")
