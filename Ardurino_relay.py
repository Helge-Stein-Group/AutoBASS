import serial
import time
import notify as nf

class Ardurelay():
    
    def __init__(self, ardu_port):
        self.ardu_port = ardu_port

    def connect_relay(self):
        nf.log_print(f'initiating Arduino_Relay on PORT: {self.ardu_port}...')
        self.serialcomm = serial.Serial(port = self.ardu_port, baudrate = 9600, timeout = 1)
        time.sleep(0.05)
        nf.log_print(f'Initiating Arduino_Relay complete')
    
    def read(self):
        read_val = ''
        for i in range(10):
            read_val = self.serialcomm.readline().decode('ascii')
            time.sleep(0.1)
            if read_val != '':
                break
            elif i == 10:
                read_val = "Read timeout"
        return read_val

    def operate_relay(self, relayNr, state):
        nf.log_print(f'Relay_{relayNr} is {state}!')
        cmd = "{}_{}".format(str(relayNr),str(state))
        self.serialcomm.write(cmd.encode())
        #ardu_return = self.read()
        #return ardu_return
    
    def disconnect_relay(self):
        self.serialcomm.close()
        return 'Arduino_Relay disconnected!'
