import telnetlib
import socket
import time
import notify as nf

RAIL_HOST = "192.168.31.233"
RAIL_PORT = 10001

class Rail():
    def __init__(self):
        pass
            
    def read_intelligent(self):
    # Read the echo from Linear Motor Axis
        read_vals = []
        for i in range(10):
            read = self.session.read_until(b'\r',timeout=0.01)
            if read == b'':
                break
            else:
                read_vals.append(read)
        return read_vals
        
    def connect_rail(self,host = RAIL_HOST,port = RAIL_PORT,timeout = 2):
    # Establish connection with the Linear Motor Axis via telnet
        nf.log_print('Initiating Linear Motor Axis...')
        try:
            self.session = telnetlib.Telnet(host, port, timeout)
        except socket.timeout:
            nf.log_print("Another user is already in connection!")
        else:
            nf.log_print("Checking for reference status...")
            self.session.write(b"evt1\r")

            # Check for reference status
            check_reference = self.read_intelligent()
            if check_reference[check_reference.index(b'evt1\r')+2] ==  b'\n>@H\r':
                nf.log_print("Reference already completed!")
            else:
                nf.log_print("Referencing position...")
                self.session.write(b"ref\r")
                time.sleep(10)
                nf.log_print("Homing linear motor...")
                self.move(0)
        finally:
            self.session.write(b"evt1\r")
            connection_returns = self.read_intelligent()
        return connection_returns[connection_returns.index(b'evt1\r')+2] == b'\n>@H\r'

    def set_vel(self, vel):
    # Accelerate or decelerate the moving speed
        cmd = f"SPI {int(vel*1000)}\r".encode()
        self.session.write(cmd)
        self._velocoty = vel

    def get_actual_vel(self):
    # Tell the current speed
        cmd = f"TV\r".encode()
        self.session.write(cmd)
        res = float(self.read_intelligent()[1])/1000
        return res
        
    def check_move(self, check_pos):
    # Block the next movement
        if self.getStatus() == True and abs(self.getPosition()-float(check_pos)) <= 0.1:
            nf.log_print(f"Abs_Position reached: {self.getPosition()}mm; Processing time: {self.getProcessTime()}ms")
        else:
            time.sleep(0.1)
            self.check_move(check_pos)
    
    def getProcessTime(self):
    # Tell the time used for last movement
        self.session.write(b"tmt\r")
        try:
            processing_time_ms = int(self.read_intelligent()[1])
        except:
            return None
        else:
            return processing_time_ms

    def getPosition(self):
    # Tell the current position of Linear Motor in mm
        try:
            self.session.write(b"TP\r")
            returns = self.read_intelligent()
            mmpos = float(returns[1])/1000
        except:
            mmpos = -1
        return mmpos
    
    def getStatus(self):
    # Tell the current status of Linear Motor Axis, status= 1: the Linear Motor Axis is stopped, status= 0: the Linear Motor is in motion
        try:
            self.session.write(b"TS\r")
            time.sleep(0.1)
            status = self.read_intelligent()
            if int(status[1]) == 1:
                motor = True
            else:
                motor = False
        except:
            motor = False
        return motor

    def _rail_online(self):
    # Tell if the rail is online
        self.session.write(b"evt1\r")
        connection_returns = self.read_intelligent()
        return connection_returns[connection_returns.index(b'evt1\r')+2] == b'\n>@H\r'

    def move(self,pos_abs):
    # Drive the Linear Motor Axis into expected position, argument's unit in mm
        time.sleep(0.1)
        cmd = f"G {int(pos_abs*1000)}\r".encode()
        self.session.write(cmd)
        self.check_move(check_pos=pos_abs)
        return True

    def rel_move(self, pos_rel):
        pos_temp = self.getPosition()
        time.sleep(0.1)
        target_step = int(pos_rel*1000)
        set_cmd = f"WA {target_step}\r".encode()
        self.session.write(set_cmd)
        time.sleep(0.1)
        move_cmd = f"GW\r".encode()
        self.session.write(move_cmd)
        self.check_move(pos_temp+pos_rel)
        return True

    def stopMotion(self):
        self.session.write(b"SM\r")

    def disconnect_rail(self):
    # Disconnect with the Linear Motor, power_statu = 1: Linear MOtor still connected, power_statu = 2 : Linear Motor disconnected
        nf.log_print('Shutting down Linear Motor Axis...')
        msg = self.move(0)
        if msg is True:
            self.session.write(b"PQ\r")
            temp = self.read_intelligent()
            if temp[1] == b'\n>@S0\r':
                self.session.close()
                nf.log_print("Linear axis disconnected!")

    def removeerror(self):
        pass