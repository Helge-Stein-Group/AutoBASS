from Ardurino_relay import Ardurelay
import notify as nf

class Crimper(Ardurelay):
    def __init__(self, crimper_port = 'COM3'):
        Ardurelay.__init__(self, crimper_port)
        
    def connect_crimper(self):
        self.connect_relay()
        self._crimper_is_online = True
        nf.log_print("Control on crimper established")

    def turn_on(self, wait_time=75, conf = False):
        if conf is True:
            nf.log_print('Start crimping...')
            self.operate_relay(1, "pulse")
            nf.count_down_print(count_msg="Crimping Machine operating, keep away!", end_msg="Complete!", count_time=wait_time)
            nf.log_print("Crimping complete")
            return True
        else:
            nf.log_print("Crimpping cannot be commenced due to unfinished movement of robot or rail")
            return False
    
    def disconnect_crimper(self):
        self.disconnect_relay()
        self._crimper_is_online = False
        nf.log_print("Crimper disconnected")
