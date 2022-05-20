import os
import time
import json
import cv2
from Ardurino_relay import Ardurelay
from MecademicRobot import RobotController
import notify as nf

PATH = os.path.dirname(__file__)
# IP address of robots
ASSEMBLY_HOST = "192.168.31.231"
TRANSPORT_HOST = "192.168.31.232"

# Arduino port
ARDU_PORT = 'COM8'

# Camera port
CAM_PORT = 1

# Robot Constant
os.chdir(f"{PATH}\data")

# Get latest constant values from config file
with open('config.json') as json_file:
    CONSTANT = json.load(json_file)
TCP_SK = CONSTANT['TCP_SK']
TCP_GP = CONSTANT['TCP_GP']
TCP_CP = CONSTANT['TCP_CP']
TCP_CP_180 = CONSTANT['TCP_CP_180']

class AssemblyRobot(RobotController, Ardurelay):

    def __init__(self, address=ASSEMBLY_HOST, vacuum_port=ARDU_PORT):
        RobotController.__init__(self, address)
        Ardurelay.__init__(self, vacuum_port)
        self.address = address

    def initiate_robot(self):
        # Activate robot, home, reset joints, apply parameters
        nf.log_print('Initiating AssemblyRobot...')
        self.connect_relay()
        msg = self.connect()
        time.sleep(0.1)
        if msg is True:
            msg = self.ActivateRobot()
            time.sleep(0.1)
            if msg == 'Motors activated.':
                msg = self.home()
                time.sleep(0.1)
                if msg == 'Homing done.':
                    # Set robot's parameter
                    self.SetCartLinVel(CONSTANT['L_VEL'])
                    self.SetJointVel(CONSTANT['J_VEL'])
                    self.SetJointAcc(50)
                    self.SetGripperForce(CONSTANT['GRIP_F'])
                    self.SetGripperVel(CONSTANT['GRIP_VEL'])
                    self.MoveJoints(0,0,0,0,0,0)
                    time.sleep(0.01)
                    nf.log_print('AssemblyRobot initiated.')
                    self.cam = cv2.VideoCapture(CAM_PORT)
                    nf.log_print('Camera online.')
                else:
                    nf.log_print('AssemblyRobot already homed!')
            else:
                nf.log_print('AssemblyRobot already activated!')
        elif msg == 'Another user is already connected, closing connection':
            nf.log_print('AssemblyRobot already in connection!')
        else:
            nf.log_print('AssemblyRobot is not in connection. Check Power buttom')

    def snap_shot(self, filename=''):
    # Ultilize the Webcam to capture image during manufacturing
        self.cam.open(CAM_PORT)
        discard_count = 0
        while discard_count < 2:
            ret, frame = self.cam.read()
            if ret is True:
                discard_count += 1
            time.sleep(0.5)
        os.chdir(f"{PATH}\Alignments")
        time_stamp = time.strftime("%d_%m_%Y_%Hh_%Mm_%Ss", time.localtime())
        if filename:
            filename = f"{filename}_{time_stamp}.jpg"
        else:
            filename = f"{time_stamp}.jpg"
        cv2.imwrite(filename, frame)
        self.cam.release()
        cv2.imshow(f"Image{filename}", frame)
        cv2.waitKey(2000)
        cv2.destroyAllWindows()

    def grab_component(self, grab_po):
    # Grabing materials from trays
        nf.log_print(f"Gripping on {grab_po}...")

        # Grab the component
        time.sleep(0.01)

        # Determine which tool to use for grabing
        if abs(grab_po[0]) >= 160:
        # Switch the TCP, Reset the joints' position
            self.SetTRF(*TCP_GP)
            time.sleep(0.1)
            self.MoveJoints(*CONSTANT['HOME_GP_J'])

            # Move to the start position
            self.MovePose(grab_po[0], grab_po[1], 40, grab_po[3], grab_po[4], grab_po[5])
            self.GripperOpen()
            time.sleep(0.5)

            # Gripper goes down
            self.MoveLin(*grab_po)
            time.sleep(0.5)

            # Gripping parts, ready to transport
            self.GripperClose()
            time.sleep(1)
            self.MoveLin(grab_po[0], grab_po[1], 40, grab_po[3], grab_po[4], grab_po[5])
            self.MoveJoints(*CONSTANT['HOME_GP_J'])

        elif abs(grab_po[0]) < 160:
        # Switch the TCP, Reset the joints' position
            self.SetTRF(*TCP_SK)
            time.sleep(0.1)
            self.MoveJoints(*CONSTANT['HOME_SK_J'])
            
            # Robot move to the start position
            self.MovePose(grab_po[0], grab_po[1], 40, grab_po[3], grab_po[4], grab_po[5])
            # Open Gripper settle sucktion cup into position
            self.GripperOpen()
            time.sleep(0.5)

            self.MoveLin(*grab_po)

            # Pump switching on
            self.suction_on()

            # Gripping parts, ready to transport
            time.sleep(2)
            self.MoveLin(grab_po[0], grab_po[1], 40, grab_po[3], grab_po[4], grab_po[5])
            self.MoveJoints(*CONSTANT['HOME_SK_J'])
        return True

    def drop_component(self, drop_po, component:str, nr:int):
    # Drop the material onto the post
        nf.log_print(f"Dropping on {drop_po}...")

        # Robot move to the start position
        self.MovePose(drop_po[0], drop_po[1], 100, drop_po[3], drop_po[4], drop_po[5])
        time.sleep(0.5)

        # Gripper goes down, and drop the parts
        self.MoveLin(*drop_po)

        time.sleep(0.5)
        if component == 'spring':
            time.sleep(1)
            self.GripperOpen()
            time.sleep(2)
        elif component == 'cathode case':
            # Perform tilling movement
            self.SetCartAngVel(5)
            self.MoveLinRelWRF(0.5,0,0.5,0,0,0)
            self.MoveLinRelWRF(0,0,0,0,2,0)
            self.MoveLinRelWRF(0,0,-1.5,0,0,0)
            self.MoveLinRelWRF(0,0,0,0,-2,0)
            self.suction_off()
            # Wait for enough time to release the vacuum
            time.sleep(4)
            self.SetCartAngVel(45)
        elif component in ('anode', 'separator', 'cathode'):
            self.SetCartAngVel(90)
            self.suction_off()
            # Wait for enough time to release the vacuum
            time.sleep(6)
            self.MoveLinRelWRF(0,0,10,0,0,0)
            self.SetCartAngVel(45)
            # Taking a snap shot
            nf.log_print(f'Taking snap shot on {component}', logfile='assembly')
            self.MoveJoints(*CONSTANT['SNAP_SHOT_J'])
            self.snap_shot(f"{component}_No{nr}")
            nf.log_print(f'Snap shot taken', logfile='assembly')
        elif component in ('anode case', 'anode spacer', 'cathode spacer'):
            self.suction_off()
            # Wait for enough time to release the vacuum
            time.sleep(6)
            
        # Homing the robot
        self.MoveLinRelWRF(0,0,30,0,0,0)
        self.MovePose(drop_po[0], drop_po[1], drop_po[2]+60, drop_po[3], drop_po[4], drop_po[5])
        self.MoveJoints(*CONSTANT['HOME_POST_J'])
        self.MoveJoints(*CONSTANT['HOME_SK_J'])
        return True

    def press_cell(self):
    # Press cathode case
        nf.log_print("Pressing...")
        
        self.SetTRF(*TCP_GP)
        time.sleep(0.1)

        self.MoveJoints(*CONSTANT['HOME_GP_J'])
        self.MovePose(*CONSTANT['PRESS_1_PO'])
        time.sleep(0.5)
        
        # Performing pressing on 5 points
        self.GripperOpen()
        self.MoveLin(*CONSTANT['PRESS_2_PO'])
        # Change press point to x:+2 and press again
        self.MoveLinRelWRF(0,0,5,0,0,0)
        self.MoveLinRelWRF(2,0,0,0,0,0)
        self.MoveLinRelWRF(0,0,-5,0,0,0)
        # Change press point to x:-4 and press again
        self.MoveLinRelWRF(0,0,5,0,0,0)
        self.MoveLinRelWRF(-4,0,0,0,0,0)
        self.MoveLinRelWRF(0,0,-5,0,0,0)
        # Change press point to y:-2 and press again
        self.MoveLinRelWRF(0,0,5,0,0,0)
        self.MoveLinRelWRF(2,-2,0,0,0,0)
        self.MoveLinRelWRF(0,0,-5,0,0,0)
        # Change press point to y:+4 and press again
        self.MoveLinRelWRF(0,0,5,0,0,0)
        self.MoveLinRelWRF(0,4,0,0,0,0)
        self.MoveLinRelWRF(0,0,-5,0,0,0)
        # Change press point to x:-2 and press again
        self.MoveLinRelWRF(0,0,5,0,0,0)
        self.MoveLinRelWRF(0,-2,0,0,0,0)
        self.MoveLinRelWRF(0,0,-6,0,0,0)
        self.MoveLinRelWRF(0,0,6,0,0,0)
        time.sleep(0.5)

        # Move up
        self.MoveLin(CONSTANT['PRESS_2_PO'][0], CONSTANT['PRESS_2_PO'][1], CONSTANT['PRESS_2_PO'][2]+15, CONSTANT['PRESS_2_PO'][3], CONSTANT['PRESS_2_PO'][4], CONSTANT['PRESS_2_PO'][5])

        # Reset joints' position
        self.MoveJoints(*CONSTANT['HOME_POST_J'])
        self.MoveJoints(*CONSTANT['HOME_GP_J'])
        return True

    def retrieve_cell(self):
    # Grab finished cell on the post
        retrieve_po = CONSTANT['POST_C_PO']
        nf.log_print(f"Retrieving cell on Post...")

        # Robot move above the post
        self.SetTRF(*TCP_SK)
        self.MovePose(retrieve_po[0], retrieve_po[1], 70, retrieve_po[3], retrieve_po[4], retrieve_po[5])
        self.GripperOpen()

        # Get the cell
        self.MoveLin(*retrieve_po)
        time.sleep(0.5)
        self.suction_on()
        time.sleep(2)
        
        # Home robot
        self.MoveLin(retrieve_po[0], retrieve_po[1], 70, retrieve_po[3], retrieve_po[4], retrieve_po[5])
        self.MoveJoints(*CONSTANT['HOME_SK_J'])
        return True

    def store_cell(self, store_po):
    # Put back finished cell
        nf.log_print(f"Storing cell on {store_po}...")

        # Robot move to tray position
        self.MovePose(store_po[0]-2, store_po[1], 40, store_po[3], store_po[4]-5, store_po[5])
        time.sleep(0.5)

        # Drop cell
        self.MoveLin(store_po[0]-2, store_po[1], store_po[2]+4, store_po[3], store_po[4]-5, store_po[5])
        time.sleep(0.5)
        self.suction_off()
        self.SetCartAngVel(5)
        self.MoveLinRelWRF(3,0,-3,0,0,0)
        self.MoveLinRelTRF(0,0,0,-5,0,0)
        time.sleep(1)
        self.SetCartAngVel(45)
        # Empty Gripper goes up using MovePose for fast mode
        self.go_home()
        return True

    def suction_on(self):
        self.operate_relay(2, "on")

    def suction_off(self):
        self.operate_relay(2, "off")

    def go_home(self):
        nf.log_print("Homing AssemblyRobot...")
        self.auto_repair()
        temp_po = list(self.GetPose())
        if abs(temp_po[0]) >= 170:
            standby = CONSTANT['HOME_GP_J']
        if abs(temp_po[0]) < 170:
            standby = CONSTANT['HOME_SK_J']
        if temp_po[2] <= 80:
            self.MoveLinRelWRF(0,0,40,0,0,0)
            time.sleep(0.5)
        self.MoveJoints(*standby)

    def auto_repair(self):
    # If there is an error we try to autorepair it. Added an extra resume motion over the
    # mecademic suggested version
        if self.is_in_error():
            self.ResetError()
        elif self.GetStatusRobot()['Paused'] == 1:
            self.ResumeMotion()
        self.ResumeMotion()
        self.ResumeMotion()

    def disconnect_robot(self):
    # Deactivate and disconnect the robot
        nf.log_print('Disconnecting AssemblyRobot...')
        self.go_home()
        time.sleep(1.5)
        self.DeactivateRobot()
        time.sleep(0.1)
        self.suction_off()
        self.disconnect_relay()
        self.disconnect()
        time.sleep(0.1)
        nf.log_print(f"AssemblyRobot disconnected!")


class TransportRobot(RobotController):

    def __init__(self, address=TRANSPORT_HOST):
        RobotController.__init__(self, address)
        self.address = address

    def refresh_data(self):
    # RefreshPosition Constant
        os.chdir(f"{PATH}\data")
        with open('config.json') as json_file:
            CONSTANT = json.load(json_file)
        nf.log_print("Transport Robot: Position data loaded")

    def initiate_robot(self):
    # Activate robot, home, reset joints, set essential parameters
        #Load constant pos
        self.refresh_data()
        nf.log_print('Initiating TransportRobot...')
        
        msg = self.connect()
        time.sleep(0.1)
        if msg is True:
            msg = self.ActivateRobot()
            time.sleep(0.1)
            if msg == 'Motors activated.':
                msg = self.home()
                time.sleep(0.1)
                if msg == 'Homing done.':
                    # Set robot's parameter
                    self.SetTRF(*TCP_CP)
                    self.SetCartLinVel(CONSTANT['L_VEL'])
                    self.SetJointVel(CONSTANT['J_VEL'])
                    self.SetGripperForce(CONSTANT['GRIP_F'])
                    self.SetGripperVel(CONSTANT['GRIP_VEL'])
                    self.MoveJoints(*CONSTANT['WAIT_1_J'])
                    time.sleep(0.01)
                    nf.log_print('TransportRobot initiated.')
                else:
                    nf.log_print('TransportRobot already homed!')
            else:
                nf.log_print('TransportRobot already activated!')
        elif msg == 'Another user is already connected, closing connection':
            nf.log_print('TransportRobot already in connection!')
        else:
            nf.log_print('TransportRobot is not in connection! Check Power buttom!')

    def align_cell(self):
    # Line up the components on the post
        nf.log_print("Aligning cell...")

        # To the start posiiton
        self.SetTRF(*TCP_CP)
        self.MoveJoints(*CONSTANT['WAIT_2_J'])
        self.MovePose(*CONSTANT['ALIGN_1_PO'])

        # Gripper goes down to position
        self.GripperOpen()
        time.sleep(0.5)
        self.MoveLin(*CONSTANT['ALIGN_2_PO'])
        self.SetGripperVel(CONSTANT['GRIP_VEL']*0.5)
        self.SetGripperForce(CONSTANT['GRIP_F']*0.5)
        time.sleep(0.5)
        self.GripperClose()
        time.sleep(1)
        self.GripperOpen()
        time.sleep(1)
        self.GripperClose()
        time.sleep(2)
        self.SetGripperForce(CONSTANT['GRIP_F'])
        self.SetGripperVel(CONSTANT['GRIP_VEL'])
        self.GripperOpen()
        time.sleep(1)

        # Gripper goes up
        self.MoveLin(*CONSTANT['ALIGN_1_PO'])

        # Home robot
        self.MoveJoints(*CONSTANT['WAIT_2_J'])
        self.MoveJoints(*CONSTANT['WAIT_1_J'])
        return True

    def send_to_crimper(self):

        # Send the assemblyed cell into crimper, to avoid sigularity, two phases of movement should performed in order
        nf.log_print("Sending cell into crimper...")

        # To the start posiiton
        self.SetTRF(*TCP_CP_180)
        self.MoveJoints(*CONSTANT['WAIT_2_J'])
        self.MovePose(*CONSTANT['GRIP_1_PO'])

        # Gripper goes down to position
        self.GripperOpen()
        time.sleep(0.5)
        self.MoveLin(*CONSTANT['GRIP_2_PO'])
        time.sleep(0.5)
        self.GripperClose()
        time.sleep(1)

        # Gripper goes up
        self.MoveLin(*CONSTANT['GRIP_1_PO'])

        # Set TCP back to normal
        self.SetTRF(*TCP_CP)

        # Reduce the rotating radius, rotate to crimper
        self.MoveJoints(*CONSTANT['ROTATE_LEFT_J'])
        self.MoveJoints(*CONSTANT['ROTATE_RIGHT_J'])

        # Drive through sigularity, ready to reach in
        self.MoveJoints(*CONSTANT['TRANS_1_J'])
        time.sleep(0.5)

        # Reaching into crimper next to the die:
        self.MoveLin(*CONSTANT['TRANS_2_PO'])
        time.sleep(0.5)

        # Droping CC into the die:
        self.MoveLin(*CONSTANT['TRANS_3_PO'])
        time.sleep(0.5)
        self.GripperOpen()
        time.sleep(0.5)

        # Move the gripper away from die
        self.MoveLin(*CONSTANT['BACKOFF_1_PO'])
        self.MoveLin(*CONSTANT['BACKOFF_2_PO'])
        self.MoveLin(*CONSTANT['BACKOFF_3_PO'])

        # Move out from crimper, goes to waitng position, ready to use the magenetic part
        self.MoveJoints(*CONSTANT['RETRIVE_1_J'])
        return True

    def pickup_from_crimper(self):
    # Get cell from crimper-die
        nf.log_print("Retrieving cell from crimper...")

        # Set TCP to normal:
        self.SetTRF(*TCP_CP)
        
        # Magnet reaching into the crimper next to the die:
        self.MoveLin(*CONSTANT['RETRIVE_2_PO'])

        # Above the die, magnetic Grabing:
        self.MoveLin(*CONSTANT['RETRIVE_3_PO'])
        time.sleep(1)

        # Move up 3 mm:
        self.MoveLin(*CONSTANT['RETRIVE_4_PO'])

        # Move the Magnet with CC away from die: Backwards
        self.MoveLin(*CONSTANT['RETRIVE_5_PO'])

        # Move to the ROTATION_RIGHT:
        self.MoveJoints(*CONSTANT['ROTATE_RIGHT_J'])

        # Move to the ROTATION_LEFT:
        self.MoveJoints(*CONSTANT['ROTATE_LEFT_J'])

        # Ready to drop the CC on Post::
        self.MovePose(*CONSTANT['RETRIVE_6_PO'])

        # Drop CC on the Post:
        self.MoveLin(*CONSTANT['RETRIVE_7_PO'])
        time.sleep(0.5)

        # Perform Sliding:
        self.MoveLin(*CONSTANT['RETRIVE_8_PO'])

        # Move up, home the position
        self.MoveLinRelWRF(0,0,15,0,0,0)
        self.MoveJoints(*CONSTANT['WAIT_2_J'])
        self.MoveJoints(*CONSTANT['WAIT_1_J'])
        return True
        
    def go_home(self):
        nf.log_print("Homing TransportRobot...")

        # Home the TransportRobot
        self.auto_repair()
        current_j = list(self.GetJoints())
        current_po = list(self.GetPose())
        if current_j[0] < 120 and current_j[0] > 0:
            if current_po[1] > 195:
                # Now the gripper is inside of crimper
                # Lift up the gripper to safety z
                self.MoveLin(current_po[0], current_po[1], 322.150, current_po[3], current_po[4], current_po[5])
                current_po = self.GetPose()
                time.sleep(0.5)

                # Move the gripper to the left to safty x
                self.MoveLin(-18, current_po[1], current_po[2], current_po[3], current_po[4], current_po[5])
                current_po = self.GetPose()
                time.sleep(0.5)

                # Move the gripper backwards to safty y value
                self.MoveLin(current_po[0], 193, current_po[2], current_po[3], current_po[4], current_po[5])
            self.MoveJoints(*CONSTANT['ROTATE_RIGHT_J'])
            self.MoveJoints(*CONSTANT['ROTATE_LEFT_J'])
            self.MoveJoints(*CONSTANT['WAIT_2_J'])
            
        elif current_j[0] < 0 and current_j[0] > -120:
            if current_po[2] < 120:
                # Now the gripper is near the post
                # Lift up the gripper to safety z
                self.MoveLin(current_po[0], current_po[1], 200, current_po[3], current_po[4], current_po[5])
                self.SetTRF(*TCP_CP)
            self.MoveJoints(*CONSTANT['ROTATE_LEFT_J'])
            self.MoveJoints(*CONSTANT['WAIT_2_J'])
        self.MoveJoints(*CONSTANT['WAIT_1_J'])

    def auto_repair(self):
    # If there is an error we try to autorepair it. Added an extra resume motion over the
    # mecademic suggested version
        if self.is_in_error():
            self.ResetError()
        elif self.GetStatusRobot()['Paused'] == 1:
            self.ResumeMotion()
        self.ResumeMotion()
        self.ResumeMotion()
        
    def disconnect_robot(self):
    # Deactivate and disconnect the robot
        nf.log_print('Disconnecting TransportRobot')
        self.go_home()
        time.sleep(1.5)
        self.DeactivateRobot()
        time.sleep(0.1)
        self.disconnect()
        time.sleep(0.1)
        nf.log_print("TransportRobot disconnected!")