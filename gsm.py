import time
from machine import UART, Pin

MODEM_PWR_PIN = Pin(4, Pin.OUT)
# time.sleep_ms(5000)
MODEM_PWR_PIN.value(0)
time.sleep_ms(300)
MODEM_PWR_PIN.value(1)
# Wait for power on
time.sleep_ms(5000)
uart = UART(1, 9600, timeout=1000, rx=26, tx=27)

# Clear the buffer
uart.readline()

out = uart.readline()
while out is None or out.strip() != b'AT':
    print('trying...')
    uart.write("AT\r\n".encode())
    if out is not None:
        print(out.strip())
    out = uart.readline()
print(out.strip())

while (out := uart.readline()) is not None:
    print(out.strip())



