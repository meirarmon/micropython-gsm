import time
from machine import UART, Pin


class SIMCOM7000:
    def __init__(self, *, modem_pwr_pin, rx, tx):
        self.pwr_pin = Pin(modem_pwr_pin, Pin.OUT)
        self.uart = UART(1, 9600, timeout=500, rx=rx, tx=tx)
        self.init()

    def init(self):
        self.pwr_pin.value(0)
        time.sleep_ms(300)
        self.pwr_pin.value(1)
        # Wait for power on
        time.sleep_ms(5000)

        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < 20_000:
            if self.send_cmd('AT', timeout=500):
                break
        else:
            raise Exception("Could not initialize")

        time.sleep_ms(3000)

        # Empty the uart buffer just in case
        while _ := self.uart.readline():
            continue

    def wait_for(self, output, timeout=5000):
        full_output = []
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < timeout:
            while out := self.uart.readline():
                out = out.strip()
                full_output.append(out)
                print(f"<== {out}")
                if output.encode() in out:
                    return full_output
        return []

    def send_cmd(self, cmd, output='OK', timeout=5000):
        cmd = f'{cmd}\r\n'
        print(f'==> {cmd}')
        self.uart.write(cmd.encode())
        return self.wait_for(output, timeout)

    def send_cmd_get_resp(self, cmd):
        self.uart.write(cmd.encode())
        out = self.uart.readline()
        while out is None or out.strip() != b'OK':
            print('trying...')
            self.uart.write(cmd.encode())
            if out is not None:
                print(out.strip())
            out = self.uart.readline()
        print(out.strip())
        return out.strip()

    def get_imei(self):
        self.send_cmd_get_resp("AT+CGSN\r\n")

    def get_imsi(self):
        self.send_cmd_get_resp("AT+CIMI\r\n")

    def get_iccid(self):
        self.send_cmd_get_resp("AT+CCID\r\n")

    def get_operator(self):
        self.send_cmd_get_resp("AT+COPS?\r\n")

    def get_network_status(self):
        pass


if __name__ == '__main__':
    gsm = SIMCOM7000(modem_pwr_pin=4, rx=26, tx=27)
