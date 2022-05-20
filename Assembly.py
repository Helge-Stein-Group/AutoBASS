import time
import json
import os
import threading
import numpy as np
import Crimper
import Dispensor
import notify as nf
import Robots
import Rail

# Get the folder path
PATH = os.path.dirname(__file__)

# Assembly constant
COMPONENTS = np.array(['anode case', 'anode spacer', 'anode', 'separator', 'cathode', 'cathode spacer', 'spring', 'cathode case'])


class Assembly():
    def __init__(self):
        self.my_rail = Rail.Rail()
        self.rubi = Robots.AssemblyRobot()
        self.pangpang = Robots.TransportRobot()
        self.dispensor = Dispensor.Dispensor()
        self.badass = Crimper.Crimper()
        self._sys_is_on = None
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._pause.set()

    def load_parameter(self):
        os.chdir(f"{PATH}\data")
        with open('config.json') as json_file:
            parameter = json.load(json_file)
        self.parameter = parameter
        nf.log_print("Assembly config file loaded")
        # Format: {'Component Name': [Holer Position, Grab z value, Drop z value, [Pre-Drop Positoion], {'Component Nr.': [Pre-grab Position]}]}

    def apply_set_up(self):
        os.chdir(f"{PATH}\data")
        with open('config.json') as json_file:
            parameter = json.load(json_file)
        self.rubi.SetJointVel(parameter['J_VEL'])
        self.rubi.SetCartLinVel(parameter['L_VEL'])
        self.rubi.SetGripperVel(parameter['GRIP_VEL'])
        self.rubi.SetGripperForce(parameter['GRIP_F'])
        self.pangpang.SetJointVel(parameter['J_VEL'])
        self.pangpang.SetCartLinVel(parameter['L_VEL'])
        self.pangpang.SetGripperVel(parameter['GRIP_VEL'])
        self.pangpang.SetGripperForce(parameter['GRIP_F'])
        self.dispensor.config_volume()
        #self.my_rail.set_vel(parameter['AX_VEL'])

    def initiate_all(self):
        self._progress = dict(cell_nr=None, component=None, status=0)
        try:
            self.my_rail.connect_rail()
            self._progress.update(component='Rail', status=20)
            self.rubi.initiate_robot()
            self._progress.update(component='AssemblyRobot', status=40)
            self.pangpang.initiate_robot()
            self._progress.update(component='TransportRobot', status=60)
            self.dispensor.connect_dispensor()
            self._progress.update(component='Dispensor', status=80)
            self.badass.connect_crimper()
            self._progress.update(component='Crimper', status=100)
        except:
            self._sys_is_on = False
        else:
            self._sys_is_on = self.check_sys_sts()

    def one_cell(self, component_Nr:int):
        # Load config file
        self.load_parameter()
        time.sleep(0.1)
        #Perform the whole assembly procedure for just one time
        self._stop.clear()
        self._progress.update(cell_nr=component_Nr, component=None, status=0)

        for component in COMPONENTS:

            # Calculate the position for individual cell-Nr.
            grab_po = self.parameter[component]['grabPo'][str(component_Nr)]
            drop_po = self.parameter[component]['dropPo'][str(component_Nr)]
            holder_pos =  self.parameter[component]['railPo'] + (component_Nr-1)//8*23

            nf.log_print(f"Processing {component} of NO. {component_Nr}:", logfile='assembly')
            self._progress.update(component=component)
            
            # Rail move to the start position
            # Pause/abort flag
            self._pause.wait()
            if self._stop.isSet():
                self.home_all()
                return

            nf.log_print(f'Moving to tray [{component}]', logfile='assembly')
            self.my_rail.move(holder_pos)
            self._progress['status'] += 1

            # Grip COMPONENTS from the tray
            # Pause/abort flag
            self._pause.wait()
            if self._stop.isSet():
                self.home_all()
                return

            nf.log_print(f'Grabing {component}', logfile='assembly')
            self.rubi.grab_component(grab_po)
            self._progress['status'] += 1

            # Drive the rail to drop position
            # Pause/abort flag
            self._pause.wait()
            if self._stop.isSet():
                self.home_all()
                return

            nf.log_print(f'Transporting {component} to post', logfile='assembly')
            self.my_rail.move(self.parameter['post'])
            self._progress['status'] += 1

            # Drop COMPONENTS on the post
            # Pause/abort flag
            self._pause.wait()
            if self._stop.isSet():
                self.home_all()
                return

            nf.log_print(f'Dropping {component} on post', logfile='assembly')
            self.rubi.drop_component(drop_po, component, component_Nr)
            self._progress['status'] += 1
            time.sleep(0.5)

            # Drop electrolyt onto the anode and separator
            # Pause/abort flag
            self._pause.wait()
            if self._stop.isSet():
                self.home_all()
                return

            self.dispensor.add_electrolyte(component)
            self._progress['status'] += 1

        # Rail move to nearby position to avoid collision
        # Pause/abort flag
        self._pause.wait()
        if self._stop.isSet():
            self.home_all()
            return

        nf.log_print("Assembly Robot moving away", logfile='assembly')
        self.my_rail.move(600)
        self._progress['status'] += 6

        # Align the components with TransportRobot
        # Pause/abort flag
        self._pause.wait()
        if self._stop.isSet():
            self.home_all()
            return

        nf.log_print("Aligning cell on post", logfile='assembly')
        self.pangpang.align_cell()
        self._progress['status'] += 6

        # Rail move to post again, ready to press
        # Pause/abort flag
        self._pause.wait()
        if self._stop.isSet():
            self.home_all()
            return

        nf.log_print("Assembly Robot moving back to post", logfile='assembly')
        self.my_rail.move(self.parameter['post'])
        self._progress['status'] += 6

        # Press the cell with gripper
        # Pause/abort flag
        self._pause.wait()
        if self._stop.isSet():
            self.home_all()
            return

        nf.log_print('Pressing COMPONENTS on the post', logfile='assembly')
        self.rubi.press_cell()
        self._progress['status'] += 6
        time.sleep(0.5)

        # Rail move to the home position to avoid collision
        # Pause/abort flag
        self._pause.wait()
        if self._stop.isSet():
            self.home_all()
            return

        nf.log_print('Assembly Robot moving Home, ready for crimping', logfile='assembly')
        self.my_rail.move(600)
        self._progress['status'] += 6

        # Send cell to the crimper
        # Pause/abort flag
        self._pause.wait()
        if self._stop.isSet():
            self.home_all()
            return

        nf.log_print("Sending cell to the crimper", logfile='assembly')
        send = self.pangpang.send_to_crimper()
        self._progress['status'] += 6

        # Crimp the assemblyed cell, default time to wait = 85s
        # Pause/abort flag
        self._pause.wait()
        if self._stop.isSet():
            self.home_all()
            return

        nf.log_print("Starting crimping", logfile='assembly')
        self.badass.turn_on(conf=send)
        self._progress['status'] += 6
        send = None

        # Pick up the crimped cell from the machine
        # Pause/abort flag
        self._pause.wait()
        if self._stop.isSet():
            self.home_all()
            return

        nf.log_print("Collecting finished cell from crimper", logfile='assembly')
        self.pangpang.pickup_from_crimper()
        self._progress['status'] += 6
        nf.log_print(f"Cell [{component_Nr}] complete.", logfile='assembly')

        # Retrieve cell from post
        # Pause/abort flag
        self._pause.wait()
        if self._stop.isSet():
            self.home_all()
            return

        nf.log_print("Retrieving cell from post", logfile='assembly')
        self.my_rail.move(self.parameter['post'])
        self.rubi.retrieve_cell() # self.parameter[COMPONENTS[-1]]['dropPo'][str(component_Nr)]
        self._progress['status'] += 6

        # Store assemblyed cell in holder
        # Pause/abort flag
        self._pause.wait()
        if self._stop.isSet():
            self.home_all()
            return

        nf.log_print("Transporting cell to tray", logfile='assembly')
        self.my_rail.move(holder_pos)
        self.rubi.store_cell(grab_po)
        self._progress['status'] += 6
        nf.log_print(f"Storing cell complete, Cell [{component_Nr}] is now stored on Tray: [{holder_pos//225+1}]", logfile='assembly')

    def batch(self, total_Nr):
        #Perform the assembly procedure repeatly, the number of repeated times is determined by x and y-number of the last component, 
        #so the COMPONENTS on each holder should have excately the same arrangement.
        for i in range(total_Nr):
            self.one_cell(i+1)

    def check_sys_sts(self):
        try:
            rob_1_res = self.rubi.GetStatusRobot()
            rob_2_res = self.pangpang.GetStatusRobot()
            rail_res = self.my_rail._rail_online()
            crimper_res = self.badass._crimper_is_online
            stepper_res = self.dispensor._stepper_is_online
            pump_res = self.dispensor._pump_is_online
        except:
            return False
        else:
            return (rob_1_res['Activated'], rob_1_res['Homing'], rob_2_res['Activated'], rob_2_res['Homing'], rail_res, crimper_res, stepper_res, pump_res) == (1,1,1,1,1,1,1,1)

    def pause(self):
        self._pause.clear()
    
    def resume(self):
        self._pause.set()
    
    def abort(self):
        self._stop.set()
        time.sleep(0.1)
        self._pause.set()
    
    def home_all(self):
        self.rubi.go_home()
        self.pangpang.go_home()
        self.my_rail.move(0)
                    
    def power_off(self):
        #Shut down the rail and all robots
        self.rubi.disconnect_robot()
        self.my_rail.disconnect_rail()
        self.pangpang.disconnect_robot()
        self.badass.disconnect_crimper()
        self.dispensor.disconnect_dispensor()
        self._sys_is_on = False

if __name__ == '__main__':
    os.chdir(PATH)
    workflow = Assembly()
    while True:
        cmd = input("Which process do you want to commence(\"H\" for help): ")
        if cmd == 'one':
            number = input("Which cell do you want to start: ")
            while not number.isdigit:
                number = input("Please type in integers only: ")
            try:
                workflow.one_cell(int(number))
            except KeyboardInterrupt:
                nf.log_print("Mannually interupted, homing system...", logfile='assembly')
                workflow.rubi.go_home()
                workflow.my_rail.move(0)
                workflow.pangpang.go_home()
        elif cmd == 'batch':
            amount = input("Type in the batch amount: ")
            while not amount.isdigit():
                amount = input("Please type in integers only: ")
            start_number = input("Type in the start number: ")
            while not start_number.isdigit():
                start_number = input("Please type in integers only: ") 
            if amount > 0 and amount <= 64 and start_number > 0 and start_number <=64:
                for i in range(start_number, amount+1):
                    try:
                        workflow.one_cell(i)
                    except KeyboardInterrupt:
                        nf.log_print("Mannually interupted, homing system...", logfile='assembly')
                        workflow.rubi.go_home()
                        workflow.my_rail.move(0)
                        workflow.pangpang.go_home()
            else:
                print("The value is too high!")
        elif cmd == 'refresh':
            workflow.parameter = workflow.load_parameter()
        elif cmd == 'reboot':
            workflow.power_off()
            time.sleep(2)
            workflow.parameter = workflow.load_parameter()
            workflow.initiate_all()
        elif cmd == 'off':
            workflow.power_off()
        elif cmd == 'Q' or cmd == 'q':
            break
        elif cmd == 'H' or cmd == 'h':
            print("""
            -----------------------------------
            Object [workflow]
            'one'     -- Assembly one cell
            'batch'   -- Assembly a batch cell
            'reboot'  -- Power cycle the system
            'refresh' -- Refresh the position
            'off'     -- Power off the system
            'Q'       -- Quit the interface
            -----------------------------------
            """)
        else:
            print("Invalide input!")