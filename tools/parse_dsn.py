import re

with open('build/warden.dsn', 'r') as f:
    content = f.read()

# find the net block for /UART1_RX
m = re.search(r'\(net /UART1_RX\n(.*?)\n\s*\)', content, re.DOTALL)
if m:
    print(f"UART1_RX connects to: {m.group(1).strip()}")

m = re.search(r'\(net /UART1_RX_1V8\n(.*?)\n\s*\)', content, re.DOTALL)
if m:
    print(f"UART1_RX_1V8 connects to: {m.group(1).strip()}")
