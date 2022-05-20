import serial
import time
import json
import os
import sys
import clr
import numpy as np
from pydantic import BaseModel
import notify as nf

DATA_PATH = os.path.dirname(__file__)

path = r'C:\Program Files (x86)\Hamilton Company\ML600 Programming Helper Tool'

sys.path.append(path)

dlls = ['Hamilton.Components.TransportLayer.ComLink',
 		'Hamilton.Components.TransportLayer.Discovery',
 		'Hamilton.Components.TransportLayer.HamCli',
 		'Hamilton.Components.TransportLayer.Protocols',
 		'Hamilton.MicroLab.MicroLabDaisyChain',
 		'Hamilton.Module.ML600']
for dll in dlls:
    clr.AddReference(dll)

from Hamilton.Components.TransportLayer import Protocols
from Hamilton import MicroLab
from Hamilton.MicroLab import Components

# Robot Constant
os.chdir(f"{DATA_PATH}\data")
# RefreshPosition Constant
with open('config.json') as json_file:
    CONSTANT = json.load(json_file)

STEPPER_PORT = "COM4"
PUMP_IP = "192.168.31.235"
STEPS = CONSTANT['MOTOR_STEPS']

global total_volume
total_volume = CONSTANT['ELECTROLYTE_VOL']

HAMILTON_CONF = dict(left=dict(syringe=dict(volume=1000000,
                                                flowRate=50000,
                                                initFlowRate=50000),
                                    valve=dict(prefIn=1,prefOut=3)),
                        right=dict(syringe=dict(volume=1000000,
                                                flowRate=50000,
                                                initFlowRate=50000),
                                    valve=dict(prefIn=2,prefOut=1)))

class Stepper():

    def __init__(self, stepper_port):
        self.stepper_port = stepper_port

    def connect_stepper(self):
        nf.log_print(f'Establishing connection to Stepper: {self.stepper_port}')
        self.serialcomm = serial.Serial(port = self.stepper_port, baudrate = 9600, timeout = 1)
        self.setSteps(STEPS)
        self._stepper_is_online = True
        nf.log_print(f'Stepper connected')

    def switch_on(self):
        self.write('on')

    def switch_off(self):
        self.write('off')
    
    def setSteps(self, stp:int):
        steps = str(stp)
        self.serialcomm.write(steps.encode())
        return self.read()

    def move_steps(self, step:int):
        if step > 0:
            for i in range(step):
                self.write('+') 
                time.sleep(2)
            print(f'Forward for {step} steps')
        elif step < 0:
            for i in range(abs(step)):
                self.write('-')
                time.sleep(2)
            print(f'Backward for {step} steps')
        else:
            pass
        print()

    def write(self, event):
        i = event.strip()
        self.serialcomm.write(i.encode())

    def read(self):
        read_val = ''
        for _ in range(10):
            read_val = self.serialcomm.readline().decode('ascii')
            if read_val != '':
                break
            else:
                continue
        return read_val

    def disconnect_stepper(self):
        time.sleep(0.01)
        self.write('off')
        self.serialcomm.close()
        self._stepper_is_online = False
        nf.log_print('Stepper disconnected!')

class return_class(BaseModel):
   parameters: dict = None
   data: dict = None

class Hamilton:
    def __init__(self, hamilton_conf):
        self.conf = hamilton_conf

    def connect_hamilton(self):
        nf.log_print("Connecting to Microlab 600...")
        self.ml600Chain = MicroLab.DaisyChain()
        #self.discovered = self.ml600Chain.Discover(5)
        #self.ml600Chain.Connect(self.discovered[0].Address,self.discovered[0].Port)
        self.ml600Chain.Connect(PUMP_IP)

        if self.ml600Chain.get_IsConnected():
            nf.log_print("Microlab 600 connected")

        self.InstrumentOnChain = self.ml600Chain.get_ML600s()[0].get_ChainPosition()

        #setup
        self.ml600Chain.ML600s[self.InstrumentOnChain].Instrument.LeftPump.Syringe.SetSize(np.uint32(self.conf['left']['syringe']['volume']))
        self.ml600Chain.ML600s[self.InstrumentOnChain].Instrument.RightPump.Syringe.SetSize(np.uint32(self.conf['right']['syringe']['volume']))
        self.ml600Chain.ML600s[self.InstrumentOnChain].Instrument.LeftPump.Syringe.SetFlowRate(np.uint32(self.conf['left']['syringe']['flowRate']))
        self.ml600Chain.ML600s[self.InstrumentOnChain].Instrument.RightPump.Syringe.SetFlowRate(np.uint32(self.conf['right']['syringe']['flowRate']))
        self.ml600Chain.ML600s[self.InstrumentOnChain].Instrument.LeftPump.Syringe.SetInitFlowRate(np.uint32(self.conf['left']['syringe']['initFlowRate']))
        self.ml600Chain.ML600s[self.InstrumentOnChain].Instrument.RightPump.Syringe.SetInitFlowRate(np.uint32(self.conf['right']['syringe']['initFlowRate']))


        self.ml600Chain.ML600s[self.InstrumentOnChain].Instrument.Pumps.InitializeDefault()
        if self.ml600Chain.ML600s[self.InstrumentOnChain].Instrument.Pumps.AreInitialized():
            self._pump_is_online = True
            nf.log_print("Pumps are initialized")
        else:
            self._pump_is_online = False

    def pump(self,leftVol=0,rightVol=0,leftPort=0,rightPort=0,delayLeft=0,delayRight=0):
        lv = np.int32(leftVol) #in nL
        rv = np.int32(rightVol)
        lp = np.byte(leftPort) #1,2 or 9,10
        rp = np.byte(rightPort)
        dr = np.uint(delayRight) # ms
        dl = np.uint32(delayLeft)
        ret = self.ml600Chain.ML600s[self.InstrumentOnChain].Instrument.Pumps.AspirateFromPortsWithDelay(lv, rv, lp, rp, dr, dl)
        return ret

    def pumpSingleL(self, volume: int=0, times:int=1):
    #we usually had all volumes for the other pumps in microliters
    #so here we expect he input to be in microliters and convert it to nL
        volnl = volume*1000
        retl = []

        if volnl > 0:
            In = 'prefIn'
            Out = 'prefOut'
        else:
            In = 'prefOut'
            Out = 'prefIn'
        
        for _ in range(times):
            #first aspirate a negative volume through the preferred in port
            self.pump(leftVol=abs(volnl), rightVol=0, leftPort=self.conf['left']['valve'][In], rightPort=0, delayLeft=0, delayRight=0)
            res = self.pump(leftVol=abs(volnl), rightVol=0, leftPort=self.conf['left']['valve'][In], rightPort=0, delayLeft=0, delayRight=0)

            retl.append(res)
            
            #then eject through the preferred out port
            self.pump(leftVol=-abs(volnl), rightVol=0, leftPort=self.conf['left']['valve'][Out], rightPort=0, delayLeft=0, delayRight=0)
            res = self.pump(leftVol=-abs(volnl), rightVol=0, leftPort=self.conf['left']['valve'][Out], rightPort=0, delayLeft=0, delayRight=0)

            retl.append(res)

        retc = return_class(parameters= {'volumeR':volume,'times':times},
                       data = {i:retl[i] for i in range(len(retl))})
        return retc

    def getStatus(self):
        vl = self.ml600Chain.ML600s[self.InstrumentOnChain].Instrument.LeftPump.Syringe.GetRemainingVolume()
        vr = self.ml600Chain.ML600s[self.InstrumentOnChain].Instrument.RightPump.Syringe.GetRemainingVolume()
        vpl = self.ml600Chain.ML600s[self.InstrumentOnChain].Instrument.LeftPump.Valve.GetNumberedPos()
        vpr = self.ml600Chain.ML600s[self.InstrumentOnChain].Instrument.RightPump.Valve.GetNumberedPos()
        return dict(vl=vl,vr=vr,vpl=vpl,vpr=vpr)

    def moveAbs(self,leftSteps=0,rightSteps=0,leftPort=0,rightPort=0,delayLeft=0,delayRight=0):
        lv = np.int32(leftSteps) #in nL
        rv = np.int32(rightSteps)
        lp = np.byte(leftPort) #1,2 or 9,10
        rp = np.byte(rightPort)
        dr = np.uint(delayRight) # ms
        dl = np.uint32(delayLeft)
        ret = self.ml600Chain.ML600s[self.InstrumentOnChain].Instrument.Pumps.MoveAbsoluteInStepsWithDelay(lv, rv, lp, rp, dr, dl)
        return ret

    def disconnect_pump(self):
        # Aspirate a certain volume, avoid evaporation
        self.pumpSingleL(-total_volume)
        status = self.getStatus()
        self.pump(leftVol=-status['vl'],rightVol=-status['vr'],leftPort=self.conf['left']['valve']['prefOut'], rightPort=self.conf['right']['valve']['prefOut'])
        self.ml600Chain.Disconnect()
        self._pump_is_online = False

class Dispensor(Stepper, Hamilton):

    def __init__(self, stepper_port=STEPPER_PORT, hamilton_conf=HAMILTON_CONF):
        Stepper.__init__(self, stepper_port)
        Hamilton.__init__(self, hamilton_conf)

    def connect_dispensor(self):
        self.connect_stepper()
        self.connect_hamilton()

    def prime_pump(self):
        nf.log_print("Priming Pump...")
        self.pumpSingleL(total_volume)

    def config_volume(self):
        os.chdir(f"{DATA_PATH}\data")
        with open('config.json') as json_file:
            global total_volume
            total_volume = json.load(json_file)['ELECTROLYTE_VOL']
    
    def add_electrolyte(self, component):
        if component in ('anode','separator'):
            nf.log_print(f'Dropping electrolyte on {component}...', logfile='assembly')
            time.sleep(0.1)

            # Tap rotate to position
            self.switch_on()
            time.sleep(1)

            # Dropping electrolyte in half volume, unit is in µL
            self.pumpSingleL(total_volume/2)

            # Arm going home
            self.switch_off()
            nf.log_print(f'{total_volume/2}µL Electrolyte added to {component}!', logfile='assembly')
            return True

    def disconnect_dispensor(self):
        self.disconnect_stepper()
        self.disconnect_pump()
        nf.log_print("Dispensor disconnected!")