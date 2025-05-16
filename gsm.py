import time
from machine import UART, Pin


class SIMCOM7000G:
    def __init__(self, *, modem_pwr_pin, rx, tx, apn):
        self.pwr_pin = Pin(modem_pwr_pin, Pin.OUT)
        self.uart = UART(1, 9600, timeout=1000, rx=rx, tx=tx)
        self.apn = apn
        self.init()

    def init(self):
        self.pwr_pin.value(0)
        time.sleep_ms(1200)
        self.pwr_pin.value(1)
        # Wait for power on
        time.sleep_ms(5000)

        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < 20_000:
            if self.send_cmd('AT', timeout=500):
                break
        else:
            raise TimeoutError("Could not initialize")

        time.sleep_ms(3000)

        # Empty the uart buffer just in case
        while _ := self.uart.readline():
            continue

    def wait_for(self, expected, timeout=5000):
        full_output = []
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < timeout:
            while out := self.uart.readline():
                out = out.strip()
                if not out:
                    continue

                try:
                    out = out.decode()
                except UnicodeError:
                    print(f"<== {out}")
                    continue

                print(f"<== {out}")
                full_output.append(out)

                if expected in out:
                    return full_output
        return []

    def send_cmd(self, cmd, expected='OK', timeout=5000):
        print(f'==> {cmd}')
        cmd = f'{cmd}\r\n'
        self.uart.write(cmd.encode())
        return self.wait_for(expected, timeout)

    def disable_echo(self):
        self.send_cmd('ATE0')

    def disable_error_mode(self):
        self.send_cmd(f'AT+CMEE=1')

    def enable_network_time_update(self):
        self.send_cmd(f'AT+CLTS=1')

    def enable_vbat_checking(self):
        self.send_cmd(f'AT+CBATCHK=1')

    def check_sim_pin(self):
        result = self.send_cmd("AT+CPIN?")
        if '+CPIN: READY' not in result:
            raise Exception("SIM PIN is required, currently unsupported by this library")

    def check_model(self):
        result = self.send_cmd("AT+GMM")
        if 'SIMCOM_SIM7000G' not in result:
            raise Exception(f"SIMCOM_SIM7000G supported, unexpected model {result[-2]}")

    def set_gpio(self):
        self.send_cmd("AT+SGPIO=0,4,1,0")

    def set_phone_functionality(self, fun):
        self.send_cmd(f'AT+CFUN={fun}')

    def set_lte(self):
        self.send_cmd('AT+CNMP=38')

    def set_nb_iot(self):
        self.send_cmd('AT+CMNB=3')

    def set_pdp_context(self, cid, mode):
        # PDP context can also be set to PPP instead of IP
        self.send_cmd(f'AT+CGDCONT={cid},"{mode}","{self.apn}","0.0.0.0",0,0,0,0')

    def register_on_network(self, timeout=60000):
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < timeout:
            result = self.send_cmd('AT+CEREG?')
            if '+CEREG: 0,1' in result:
                break
            time.sleep_ms(500)
        else:
            raise Exception('Failure to register on network')

    # MQTT Operations
    def mqtt_connect(self):
        # TODO: Assert connected to the network?
        self.send_cmd('AT+SMCONF="CLIENTID","7000G"')
        self.send_cmd('AT+SMCONF="URL","mqtt.myproj.dev"')
        self.send_cmd('AT+SMCONN')
        # TODO: Set to hex?

    def mqtt_publish(self, topic, data):
        # TODO: QOS
        # TODO: Assert connected to the broker?
        # TODO: Publish data to specific topic
        self.send_cmd(f'AT+SMPUB="{topic}","{len(data)}",1,1')
        self.uart.write(data)

    def mqtt_subscribe(self, topic):
        # TODO: QOS
        self.send_cmd(f'AT+SMSUB="{topic}",1')

    def mqtt_unsubscribe(self, topic):
        self.send_cmd(f'AT+SMUNSUB={topic}')


# APN = "SKY"
APN = "internet.golantelecom.net.il"


def run():
    gsm = SIMCOM7000G(modem_pwr_pin=4, rx=26, tx=27, apn=APN)
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
    gsm.set_pdp_context(1, 'IP')
    # gsm.set_pdp_context(13, 'IP')
    # gsm.set_pdp_context(2, 'PPP')
    gsm.register_on_network()
    gsm.send_cmd(f'AT+CSTT="{APN}"')
    time.sleep_ms(300)
    gsm.send_cmd('AT+CIICR')
    time.sleep_ms(300)
    gsm.send_cmd('AT+CIFSR')
    time.sleep_ms(300)
    gsm.send_cmd('AT+CIPPING="174.138.9.51"', timeout=10000)
    gsm.send_cmd(f'AT+CNACT=1,"{APN}"')
    return gsm


if __name__ == '__main__':
    run()
    # gsm.send_cmd('AT+CIPSHUT')
    # gsm.send_cmd('AT+CGDCONT=?')
    # gsm.send_cmd('AT+CGATT=0')
    # gsm.send_cmd('AT+SAPBR=3,1,"Contype","GPRS"')
    # gsm.send_cmd('AT+SAPBR=3,1,"APN","SKY"')
    # gsm.send_cmd('AT+CGDCONT=1,"IP","SKY"')
    # gsm.send_cmd('AT+CGATT=1')
    # gsm.send_cmd('AT+CGACT=1,1')
    # gsm.send_cmd('AT+SAPBR=1,1')
    # gsm.send_cmd('AT+SAPBR=2,1')
    # gsm.send_cmd('AT+CIPMUX=1')
    # gsm.send_cmd('AT+CIPRXGET=1')
    # gsm.send_cmd('AT+CSTT="SKY","",""')
    # gsm.send_cmd('AT+CIICR')
    # gsm.send_cmd('AT+CIFSR;E0')
    # gsm.send_cmd('AT+CGATT?')
    # gsm.send_cmd('AT+CIFSR;E0')

    # Does this connect PPP? What about the other PDP context?
    # g.send_cmd('ATD*99#')
    # g.send_cmd('AT+CGDCONT=2,"PPP","SKY"')

    # import network
    # ppp = network.PPP(gsm.uart)
    # ppp.active(True)
    # ppp.connect()
    # print(ppp.status())
    # print(ppp.isconnected())
    # print(ppp.ifconfig())
