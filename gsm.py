import time
from machine import UART, Pin


class SIMCOM7000G:
    def __init__(self, *, modem_pwr_pin, rx, tx, apn):
        self.pwr_pin = Pin(modem_pwr_pin, Pin.OUT)
        self.uart = UART(1, 9600, timeout=500, rx=rx, tx=tx)
        self.apn = apn
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

    def disable_echo(self):
        self.send_cmd('ATE0')

    def disable_error_mode(self):
        self.send_cmd(f'AT+CMEE=0')

    def enable_network_time_update(self):
        self.send_cmd(f'AT+CLTS=1')

    def enable_vbat_checking(self):
        self.send_cmd(f'AT+CBATCHK=1')

    def check_sim_pin(self):
        result = self.send_cmd("AT+CPIN?")
        if '+CPIN: READY'.encode() not in result:
            raise Exception("SIM PIN is required, currently unsupported by this library")

    def check_model(self):
        result = self.send_cmd("AT+GMM")
        if 'SIMCOM_SIM7000G'.encode() not in result:
            raise Exception(f"SIMCOM_SIM7000G supported, unexpected model {result[-2]}")

    def set_gpio(self):
        self.send_cmd("AT+SGPIO=0,4,1,0")

    def set_phone_functionality(self, fun):
        self.send_cmd(f'AT+CFUN={fun}')

    def set_lte(self):
        self.send_cmd('AT+CNMP=38')

    def set_nb_iot(self):
        self.send_cmd('AT+CMNB=2')

    def set_pdp_context(self, cid):
        # PDP context can also be set to PPP instead of IP
        self.send_cmd(f'AT+CGDCONT={cid},"IP","{self.apn}","0.0.0.0",0,0,0,0')

    def register_on_network(self, timeout=60000):
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < timeout:
            result = self.send_cmd('AT+CEREG?')
            if '+CEREG: 0,1'.encode() in result:
                break
            time.sleep_ms(500)
        else:
            raise Exception('Failure to register on network')


if __name__ == '__main__':
    gsm = SIMCOM7000G(modem_pwr_pin=4, rx=26, tx=27, apn="SKY")
    gsm.disable_echo()
    gsm.disable_error_mode()
    gsm.enable_network_time_update()
    gsm.enable_vbat_checking()
    gsm.check_sim_pin()
    gsm.check_model()
    gsm.set_phone_functionality(0)
    gsm.set_lte()
    gsm.set_nb_iot()
    gsm.set_phone_functionality(1)
    time.sleep_ms(1000)
    gsm.set_pdp_context(1)
    gsm.set_pdp_context(13)
    gsm.register_on_network()
    # Does this connect PPP? What about the other PDP context?
    # gsm.send_cmd('ATD*99#')
