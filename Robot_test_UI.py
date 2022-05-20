import json
import os
import time
import threading
from tkinter import *
from tkinter import font
from tkinter import ttk
from tkinter import messagebox
from PIL import ImageTk,Image
from Robots import AssemblyRobot, TransportRobot
from Rail import Rail
import notify as nf

PATH = os.path.dirname(__file__) # ..../config

# IP address of robots
ASSEMBLY_HOST = "192.168.31.231"
TRANSPORT_HOST = "192.168.31.232"

# Arduino port
ARDU_PORT = 'COM8'

# Robot Constant
os.chdir(f"{PATH}\data")
# RefreshPosition Constant
with open('calibration.json') as json_file:
    CONSTANT = json.load(json_file)
TCP_SUCTION = CONSTANT['TCP_SK']
TCP_GRIP = CONSTANT['TCP_GP']
TCP_CP = CONSTANT['TCP_CP']
TCP_CP_180 = CONSTANT['TCP_CP_180']

# Assembly constant
COMPONENTS = [ 'anode case', 'anode spacer', 'anode', 'separator', 'cathode', 'cathode spacer', 'spring', 'cathode case']

# Position Constant(Joints)
HOME_SUCTION = [-90,0,0,0,60,0]
HOME_TRANS = [-170,0,0,0,0,0]
HOME_GRIP = [0,0,0,0,0,0]
CHECK_GRIP = [-42.5332,22.6423,4.7280,-30.9798,45.7080,66.0961]


class TestAssemblyRobot(AssemblyRobot, Rail):
    def __init__(self):
        Rail.__init__(self)
        AssemblyRobot.__init__(self)
        self.load_parameter()
        self.tooltyp = None
        self._assembly_sys_is_online = None

#----------------------Config functions----------------------

    def load_parameter(self):
        os.chdir(f"{PATH}\data")
        with open('calibration.json') as json_file:
            self.parameter = json.load(json_file)
        # Location parameter set for robot and rail.
        # Format: {'Component Name': [Holer Position, Grab z value, Drop z value, [Pre-Drop Positoion], {'Component Nr.': [Pre-grab Position]}]}

    def choose_tool(self, component):
        # Automatically decide which tool to choose
        if component == 'spring':
            self.SetTRF(*TCP_GRIP)
            self.standby = HOME_GRIP
            self.tooltyp = "Grip"
            print('Gripping tool selected!')
        elif component in ['cathode case', 'cathode spacer', 'separator', 'anode', 'cathode', 'anode spacer', 'anode case']:
            self.SetTRF(*TCP_SUCTION)
            self.standby = HOME_SUCTION
            self.tooltyp = "Pump"
            print('Pumping tool selected!')
        else:
            print("Input Error!")
        time.sleep(0.5)

    def get_positions(self, component, cell_nr, auto_get:bool=False):
        self.load_parameter()
        time.sleep(0.1)
        grab_po = self.parameter[component]['grabPo'][str(cell_nr)]
        tray_pos = self.parameter[component]['railPo'] + (cell_nr-1)//8*23
        drop_po = self.parameter[component]['dropPo'][str(cell_nr)]
        post_pos = self.parameter['post']
        if auto_get is True and cell_nr>1:
            if cell_nr in (9,17,25,33,41,49,57):
                grab_po = self.parameter[component]['grabPo']['1']
            else:
                # Copy the x & z coordinate from the previous cell
                grab_po[0] =self.parameter[component]['grabPo'][str(cell_nr-1)][0]
                grab_po[2] = self.parameter[component]['grabPo'][str(cell_nr-1)][2]
                # Generatate the y coordinate accroding to the first cell in coloum
                grab_po[1] = self.parameter[component]['grabPo'][str((cell_nr-1)//8*8+1)][1] - 23*((cell_nr-1)%8)
        return tray_pos, grab_po, post_pos, drop_po

#----------------------Motion functions----------------------
    def initiate_sys_rob(self):
        try:
            self.connect_rail()
            self.initiate_robot()
            nf.log_print("Initiating testing procedure for AssemblyRobot...")
        except:
            pass
        else:
            nf.log_print("System initiated!")
            self._assembly_sys_is_online = True

    def get_into_position(self, axis_po, arm_pose):
        rail_po = self.getPosition()
        time.sleep(0.1)
        if rail_po == axis_po:
            self.MovePose(arm_pose[0], arm_pose[1], arm_pose[2]+20, arm_pose[3], arm_pose[4], arm_pose[5])
        else:
            self.move(axis_po)
            self.MovePose(arm_pose[0], arm_pose[1], arm_pose[2]+20, arm_pose[3], arm_pose[4], arm_pose[5])

    def smart_grip(self):
        time.sleep(0.5)
        if self.tooltyp == 'Pump':
            self.suction_on()
            time.sleep(2)
        elif self.tooltyp == 'Grip':
            self.GripperClose()
            time.sleep(1)

    def smart_drop(self):
        time.sleep(0.5)
        if self.tooltyp == 'Pump':
            self.suction_off()
            time.sleep(6)
        elif self.tooltyp == 'Grip':
            self.GripperOpen()
            time.sleep(1)

    def grip_test(self):
        ak_p = list(self.GetPose())
        self.smart_grip()
        self.MoveLinRelWRF(0,0,20,0,0,0)
        if self.tooltyp == 'Pump':
            self.MoveJoints(*CHECK_GRIP)
            self.MoveLinRelWRF(0,0,0,0,0,90)
            time.sleep(2)
            self.MoveLinRelWRF(0,0,0,0,0,-90)
            self.MovePose(ak_p[0],ak_p[1],ak_p[2]+20,ak_p[3],ak_p[4],ak_p[5])
        elif self.tooltyp == 'Grip':
            time.sleep(2)
        self.MoveLin(*ak_p)
        self.smart_drop()

    def go_home(self):
        nf.log_print("Homing AssemblyRobot...")

        # Home the arm
        self.auto_repair()
        temp_po = list(self.GetPose())
        if temp_po[2] <= 80:
            self.MoveLinRelWRF(0,0,40,0,0,0)
            time.sleep(0.5)
        self.MoveJoints(*self.standby)

    def end_assembly_test(self):
        #Shut down the rail and all robots
        self.disconnect_robot()
        self.disconnect_rail()

    def asemb_test_rob(self):
        # Get every paramerter necessary
        tray_pos, grab_po, post_pos, drop_po = self.get_positions(self.component, self.current_nr, auto_get=auto_gen_var.get())
        
        # Choose the right tool
        self.choose_tool(self.component)
        
        if self.testmode == 'grab':
            # Get into pre-set position
            if self.current_nr in (1, 9, 17, 25, 33, 41, 49, 57):
                self.go_home()
            else:
                self.MoveLinRelWRF(0,0,10,0,0,0)
            self.get_into_position(tray_pos, grab_po)
            self.GripperOpen()
            time.sleep(0.5)

            # Get to the actual position
            self.MoveLin(*grab_po)

        elif self.testmode == 'drop':
            self.go_home()
            if self.current_nr != self.test_start_number:
                # Get return position
                return_tray, return_po, _, _ = self.get_positions(self.component, self.current_nr-1)
                self.get_into_position(return_tray, return_po)
                self.MoveLin(*return_po)
                self.smart_drop()
                self.go_home()
            # Get into pre-set position
            self.get_into_position(tray_pos, grab_po)
            self.GripperOpen()
            time.sleep(0.5)

            # Get to the actual position
            self.MoveLin(*grab_po)

            # Get the component
            self.smart_grip()
            
            self.go_home()

            # To the predrop position
            self.get_into_position(post_pos, drop_po)

            # To the actual drop position
            self.MoveLin(*drop_po)
        elif self.testmode == 'sub_grab':
            # Get into pre-set position
            self.go_home()
            self.get_into_position(tray_pos, grab_po)
            self.GripperOpen()
            time.sleep(0.5)
            self.MoveLin(*grab_po)
        elif self.testmode  == 'sub_drop':
            self.smart_grip()
            self.go_home()
            self.get_into_position(post_pos, drop_po)
            self.MoveLin(*drop_po)
        elif self.testmode  == 'sub_done':
            self.go_home()
            self.get_into_position(tray_pos, grab_po)
            self.MoveLin(*grab_po)
            self.smart_drop()
            self.go_home()

    def send_testing_cell(self):
        self.load_parameter()

        # Config the positions of testing cell
        grab_po = self.parameter['cathode case']['grabPo']['64']
        drop_po = self.parameter['cathode case']['dropPo']['64']
        tray_pos = self.parameter['cathode case']['railPo'] + 63//8*23
        post_pos = self.parameter['post']

        # Get the testing cell
        self.choose_tool('cathode case')
        time.sleep(0.1)
        self.go_home()
        self.get_into_position(tray_pos, grab_po)
        self.GripperOpen()
        time.sleep(0.5)
        self.MoveLin(grab_po[0], grab_po[1], grab_po[2]-0.5, grab_po[3], grab_po[4], grab_po[5])
        self.smart_grip()
        self.go_home()

        # Place it on post
        self.get_into_position(post_pos, drop_po)
        self.MoveLin(*drop_po)
        self.smart_drop()
        self.go_home()

        # Back to the safety place
        self.move(600)
    
    def retrieve_testing_cell(self):
        self.load_parameter()

        # Config the positions
        tray_pos = self.parameter['cathode case']['railPo'] + 63//8*23
        post_pos = self.parameter['post']
        grab_po = self.parameter['cathode case']['grabPo']['64']
        drop_po = self.parameter['cathode case']['dropPo']['64']
        
        # Adjust the position to make a flate contact
        drop_po[5] = 90
        drop_po[2] -=1
        
        # Get the testing cell on post
        self.choose_tool('cathode case')
        time.sleep(0.1)
        self.get_into_position(post_pos, drop_po)
        self.MoveLin(*drop_po)
        self.smart_grip()
        self.go_home()

        # Place it on tray
        self.get_into_position(tray_pos, grab_po)
        self.MoveLin(grab_po[0], grab_po[1], grab_po[2]+2, grab_po[3], grab_po[4], grab_po[5])
        self.smart_drop()
        self.go_home()

    def free_move_rob(self, axis, step):
        if axis == '+x':
            self.MoveLinRelWRF(0,0,1,0,0,0)
            self.MoveLinRelWRF(abs(step),0,0,0,0,0)
            self.MoveLinRelWRF(0,0,-1,0,0,0)
        elif axis == '-x':
            self.MoveLinRelWRF(0,0,1,0,0,0)
            self.MoveLinRelWRF(-abs(step),0,0,0,0,0)
            self.MoveLinRelWRF(0,0,-1,0,0,0)
        elif axis == '+y':
            self.MoveLinRelWRF(0,0,1,0,0,0)
            self.MoveLinRelWRF(0,abs(step),0,0,0,0)
            self.MoveLinRelWRF(0,0,-1,0,0,0)
        elif axis == '-y':
            self.MoveLinRelWRF(0,0,1,0,0,0)
            self.MoveLinRelWRF(0,-abs(step),0,0,0,0)
            self.MoveLinRelWRF(0,0,-1,0,0,0)
        elif axis == '+z':
            self.MoveLinRelWRF(0,0,abs(step),0,0,0)
        elif axis == '-z':
            self.MoveLinRelWRF(0,0,-abs(step),0,0,0)
        elif axis == 'rx':
            self.MoveLinRelWRF(0,0,0,step,0,0)
        elif axis == 'ry':
            self.MoveLinRelWRF(0,0,0,0,step,0)
        elif axis == 'rz':
            self.MoveLinRelWRF(0,0,0,0,0,step)
        elif axis == '+rail':
            self.rel_move(abs(step))
        elif axis == '-rail':
            self.rel_move(-abs(step))
        elif axis == '+gripper':
            self.GripperOpen()
        elif axis == '-gripper':
            self.GripperClose()
        elif axis == '+vacuum':
            self.suction_on()
        elif axis == '-vacuum':
            self.suction_off()
        elif axis == 'gripper test':
            self.grip_test()
        elif axis == 'observe position':
            act_pos = list(self.GetPose())
            self.suction_off()
            time.sleep(4)
            self.MoveLin(act_pos[0],act_pos[1],act_pos[2]+20,act_pos[3],act_pos[4],act_pos[5])
            self.MoveJoints(*self.parameter['SNAP_SHOT_J'])
            self.MoveLinRelWRF(0,0,-20,0,0,0)
        elif axis == 'return position':
            self.MoveLinRelWRF(0,0,40,0,0,0)
            self.MovePose(act_pos[0],act_pos[1],act_pos[2]+20,act_pos[3],act_pos[4],act_pos[5])
            self.MoveLin(*act_pos)
            self.suction_on()

#----------------------GUI functions----------------------

    def initiate_sys(self):
        os.chdir(f"{PATH}\images")
        prog_window = Toplevel()
        prog_window.title("Assembly Robot initializing")
        prog_window.iconbitmap("Robotarm.ico")
        prog_window.geometry('280x150')
        prog_text = StringVar()
        prog_label = Label(prog_window, textvariable=prog_text, font=ft_label, pady=10, anchor=CENTER)
        prog = ttk.Progressbar(prog_window, length=250, mode='determinate', orient=HORIZONTAL)
        prog_label.grid(row=2, column=0, columnspan=2)
        prog.grid(row=1, column=0, columnspan=2, pady=20, sticky=W+E)
        sys_init = threading.Thread(target=self.initiate_sys_rob)
        sys_init.setDaemon(True)
        sys_init.start()
        prog.start(300)
        while True:
            #prog['value'] += 1
            prog_text.set(f"Initiating System, Please Wait ({prog['value']}%)")
            prog_window.update()
            if not sys_init.is_alive():
                prog.stop()
                prog['value'] = 100
                prog_text.set(f"Initiating System, Please Wait ({prog['value']}%)")
                prog_window.update()
                time.sleep(1)
                prog_window.destroy()
                break
        prog_window.mainloop()
                

    def free_move(self):
        os.chdir(f"{PATH}\images")
        self.test_aseembly_run_window.state(newstate='iconic')
        self.free_move_window = Toplevel()

        # Set the title, icon, size of the initial window
        self.free_move_window.title("Freemove GUI")
        self.free_move_window.iconbitmap("Robotarm.ico")
        self.free_move_window.geometry("830x660")

        # Create status bar
        self.free_move_status = StringVar()
        status_label = Label(self.free_move_window, textvariable=self.free_move_status, font=ft_label, pady=10, bd=1, relief=SUNKEN, anchor=W)
        status_label.grid(row=0, column=0, columnspan=2, padx=20, sticky=W+E)
        self.free_move_status.set(f"Current Location: {self.GetPose()}, Rail: {self.getPosition()}")

        # Create the control panel
        free_move_frame = LabelFrame(self.free_move_window, text="Movement Control Panel",\
            padx=25, pady=30, borderwidth=5)
        free_move_frame.grid(row=1, column=0, padx=20, pady=10)

        # Add input box for increment to functional Panel
        free_move_frame_increm = LabelFrame(free_move_frame, text="Increment: ",\
            font=ft_label, pady=8, borderwidth=3)
        self.increment = Entry(free_move_frame_increm, width=5, borderwidth=5)
        unit = Label(free_move_frame_increm, text="mm", font=ft_label)

        free_move_frame_increm.grid(row=0, column=0, padx=10, pady=5)
        self.increment.grid(row=0, column=0)
        unit.grid(row=0, column=1)

        self.increment.insert(0, '0.2')

        free_move_frame_rxyz = LabelFrame(free_move_frame, text="α-β-γ-Axis: ",\
            font=ft_label, padx=35, borderwidth=3)
        free_move_frame_rxyz.grid(row=0, column=1)

        free_move_frame_z = LabelFrame(free_move_frame, text="Z-Axis: ",\
            font=ft_label, padx=10, pady=30, borderwidth=3)
        free_move_frame_z.grid(row=1, column=0, padx=10, pady=10)

        free_move_frame_xy = LabelFrame(free_move_frame, text="XY-Axis: ",\
            font=ft_label, padx=20, pady=30, borderwidth=3)
        free_move_frame_xy.grid(row=1, column=1, padx=10, pady=10)

        free_move_frame_rail = LabelFrame(free_move_frame, text="Rail X-Axis: ",\
            font=ft_label, padx=88, borderwidth=3)
        free_move_frame_rail.grid(row=2, column=0, columnspan=2)

        # Add buttons to the control panel
        up_btn = Button(free_move_frame_z, image=arrow_up, padx=10, pady=40, border=5,\
            borderwidth=4, command=lambda: self.free_move_control('+z'))
        down_btn = Button(free_move_frame_z, image=arrow_down, padx=10, pady=40,\
            border=5, borderwidth=4, command=lambda: self.free_move_control('-z'))
        left_btn = Button(free_move_frame_xy, image=arrow_left, padx=10, pady=40,\
            border=5, borderwidth=4, command=lambda: self.free_move_control('-x'))
        right_btn = Button(free_move_frame_xy, image=arrow_right, padx=10, pady=40,\
            border=5, borderwidth=4, command=lambda: self.free_move_control('+x'))
        forward_btn = Button(free_move_frame_xy, image=arrow_up, padx=10, pady=40,\
            border=5, borderwidth=4, command=lambda: self.free_move_control('+y'))
        backward_btn = Button(free_move_frame_xy, image=arrow_down, padx=10, pady=40,\
            border=5, borderwidth=4, command=lambda: self.free_move_control('-y'))
        
        centrer_label_1 = Label(free_move_frame_z, image=centrer, padx=10, pady=40,\
            border=5, state=DISABLED)
        centrer_label_2 = Label(free_move_frame_xy, image=centrer, padx=10, pady=40,\
            border=5, state=DISABLED)

        rx_btn = Button(free_move_frame_rxyz, text="Δα", font=ft_button,\
            border=5, borderwidth=4, command=lambda: self.free_move_control('rx'))
        ry_btn = Button(free_move_frame_rxyz, text="Δβ", font=ft_button, border=5,\
            borderwidth=4, command=lambda: self.free_move_control('ry'))
        rz_btn = Button(free_move_frame_rxyz, text="Δγ", font=ft_button, border=5,\
            borderwidth=4, command=lambda: self.free_move_control('rz'))
        rail_poitive_btn = Button(free_move_frame_rail, image=arrow_right, border=5,\
            borderwidth=4, command=lambda: self.free_move_control('+rail'))
        rail_negative_btn = Button(free_move_frame_rail, image=arrow_left, border=5,\
            borderwidth=4, command=lambda: self.free_move_control('-rail'))

        up_btn.grid(row=0, column=0, padx=10)
        down_btn.grid(row=2, column=0, padx=10)
        centrer_label_1.grid(row=1, column=0)
        left_btn.grid(row=1, column=0)
        right_btn.grid(row=1, column=2)
        forward_btn.grid(row=0, column=1)
        backward_btn.grid(row=2, column=1)
        centrer_label_2.grid(row=1, column=1)
        rx_btn.grid(row=0, column=0, padx=10)
        ry_btn.grid(row=0, column=1, padx=10)
        rz_btn.grid(row=0, column=2, padx=10)
        rail_negative_btn.grid(row=0, column=0, padx=20)
        rail_poitive_btn.grid(row=0, column=1, padx=20)

        # Create Functional Frame
        function_frame = LabelFrame(self.free_move_window, text="Function Control Panel",\
            padx=25, pady=7, borderwidth=5)
        function_frame.grid(row=1, column=1, padx=5, pady=20)

        gripper_control_frame = LabelFrame(function_frame, text="Gripper Control",\
            padx=30, pady=10, borderwidth=5)
        gripper_control_frame.grid(row=0, column=0, padx=5, pady=5)

        vacuum_control_frame = LabelFrame(function_frame, text="Vacuum Control",\
            padx=30, pady=10, borderwidth=5)
        vacuum_control_frame.grid(row=1, column=0, padx=5, pady=5)

        position_control_frame = LabelFrame(function_frame, text="Position Control",\
            padx=30, pady=10, borderwidth=5)
        position_control_frame.grid(row=2, column=0, padx=5, pady=5)

         # Add functional buttons to the functional panel
        global open_gripper_btn, close_gripper_btn, open_vacuum_btn, close_vacuum_btn, observe_btn
        open_gripper_btn = Button(gripper_control_frame, text="Open Gripper",\
            border=5, padx=24, pady=10, borderwidth=4, command=lambda: self.free_move_control('+gripper'))
        close_gripper_btn = Button(gripper_control_frame, text="Close Gripper",\
            padx=24, pady=10, border=5, borderwidth=4, command=lambda: self.free_move_control('-gripper'))
        open_vacuum_btn = Button(vacuum_control_frame, text="Open Vacuum",\
            padx=20, pady=10, border=5, borderwidth=4, command=lambda: self.free_move_control('+vacuum'))
        close_vacuum_btn = Button(vacuum_control_frame, text="Close Vacuum",\
            padx=20, pady=10, border=5, borderwidth=4, command=lambda: self.free_move_control('-vacuum'))
        test_btn = Button(position_control_frame, text="Test Position",\
            padx=25, pady=5, border=5, borderwidth=4, command=lambda: self.free_move_control('gripper test'))
        observe_btn = Button(position_control_frame, text="Observe Position",\
            padx=15, pady=5, border=5, borderwidth=4, command=lambda: self.free_move_control('observe position'))
        save_btn = Button(position_control_frame, text="Save Position",\
            padx=23, pady=5, border=5, borderwidth=4, command=self.save_position)
        
        exit_btn = Button(position_control_frame, text="Exit", padx=48, pady=5, borderwidth=4, command=self.exit_free_move)

        open_gripper_btn.grid(row=0, column=0)
        close_gripper_btn.grid(row=1, column=0, pady=5)
        open_vacuum_btn.grid(row=0, column=0)
        close_vacuum_btn.grid(row=1, column=0, pady=5)
        test_btn.grid(row=0, column=0)
        observe_btn.grid(row=1, column=0, pady=5)
        save_btn.grid(row=2, column=0)
        exit_btn.grid(row=3, column=0, pady=5)

        if self.testmode in ('drop', 'sub_drop'):
            test_btn['state'] = 'disabled'
        else:
            observe_btn['state'] = 'disabled'

        self.free_move_window.mainloop()

    def exit_free_move(self):
        self.free_move_window.destroy()
        self.test_aseembly_run_window.state(newstate='normal')
        
    def check_free_move_exe(self):
        if not self.free_move_exe.is_alive():
            self.free_move_status.set(f"Current Location: {self.GetPose()}, Rail: {self.getPosition()}")
        else:
            self.free_move_window.after(100, self.check_free_move_exe)
    
    def free_move_rob_thread(self, axis, step):
        self.free_move_exe = threading.Thread(target=self.free_move_rob, args=[axis, step])
        self.free_move_exe.setDaemon(True)
        self.free_move_exe.start()
        self.check_free_move_exe()

    def free_move_control(self, axis):
        try:
            step = float(self.increment.get())
        except ValueError:
            messagebox.showerror("Input Error!", "Only positive float is accepted")
        else:
            self.free_move_status.set("Robot is now Moving, Please Wait...")
            if axis == '+gripper':
                open_gripper_btn['state'] = 'disable'
                close_gripper_btn['state'] = 'normal'
            elif axis == '-gripper':
                open_gripper_btn['state'] = 'normal'
                close_gripper_btn['state'] = 'disable'
            elif axis == '+vacuum':
                open_vacuum_btn['state'] = 'disable'
                close_vacuum_btn['state'] = 'normal'
            elif axis == '-vacuum':
                open_vacuum_btn['state'] = 'normal'
                close_vacuum_btn['state'] = 'disable'
            elif axis == 'observe position':
                observe_btn.config(text='Return position', command=lambda: self.free_move_control('return position'))
            elif axis == 'return position':
                observe_btn.config(text='Observe position', command=lambda: self.free_move_control('observe position'))
            self.free_move_rob_thread(axis, step)

    def set_test_assembly(self):
        os.chdir(f"{PATH}\images")
        # Start a new window
        self.test_assembly_config_window = Toplevel()
        self.test_assembly_config_window.title("Assembly Robot Testing Interface")
        self.test_assembly_config_window.iconbitmap("Robotarm.ico")
        self.test_assembly_config_window.geometry("460x490")

        # Load images
        global arrow_left, arrow_right, arrow_up, arrow_down, centrer, done
        arrow_left = ImageTk.PhotoImage(Image.open("arrow_left.png"))
        arrow_right = ImageTk.PhotoImage(Image.open("arrow_right.png"))
        arrow_up = ImageTk.PhotoImage(Image.open("arrow_up.png"))
        arrow_down = ImageTk.PhotoImage(Image.open("arrow_down.png"))
        centrer = ImageTk.PhotoImage(Image.open("centrer.png"))
        done = ImageTk.PhotoImage(Image.open("done.png"))

        # Specify font of labels and button's text
        global ft_label, ft_button
        ft_label = font.Font(family='Arial', size=10, weight=font.BOLD)
        ft_button = font.Font(size=15)

        # Creat frame
        test_assembly_frame = LabelFrame(self.test_assembly_config_window, padx= 50, pady=30, borderwidth=5)
        test_assembly_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        # Creat a seris of radiobuttons for mode switching
        mode_switch_frame = LabelFrame(test_assembly_frame, text="Testing Mode:  ", padx=45, pady=10, borderwidth=2)
        mode_switch_frame.grid(row=0, column=0, columnspan=2)

        self.test_mode_input = StringVar()
        self.test_mode_input.set("grab")
 
        grip = Radiobutton(mode_switch_frame, text="Grab", variable=self.test_mode_input, value='grab')
        drop = Radiobutton(mode_switch_frame, text="Drop", variable=self.test_mode_input, value='drop')
        both = Radiobutton(mode_switch_frame, text="Both", variable=self.test_mode_input, value='both')

        grip.grid(row=0, column=1)
        drop.grid(row=0, column=2)
        both.grid(row=0, column=3)

        # Create components menu
        components_label = Label(test_assembly_frame, text="Component to Test: ", padx=15, pady=15, font=ft_label)

        components_label.grid(row=1, column=0)

        components = [
            'Anode Case',
            'Anode Spacer',
            'Anode',
            'Separator',
            'Cathode',
            'Cathode Spacer',
            'Spring',
            'Cathode Case'
        ]

        self.test_component = StringVar()

        self.test_component.set(components[0])

        drop = OptionMenu(test_assembly_frame, self.test_component, *components)
        drop.grid(row=1, column=1)

        # Creat labels
        start_number_label = Label(test_assembly_frame, text="First Cell to test:", pady=15, font=ft_label)
        end_number_label = Label(test_assembly_frame, text="Last Cell to test:", pady=15, font=ft_label)

        start_number_label.grid(row=2, column=0)
        end_number_label.grid(row=3, column=0)
        
        # Create input fields
        self.test_start_number_input = Entry(test_assembly_frame, width=10, borderwidth=5)
        self.test_end_number_input = Entry(test_assembly_frame, width=10, borderwidth=5)

        self.test_start_number_input.grid(row=2, column=1)
        self.test_end_number_input.grid(row=3, column=1)

        # Creat checkbox
        global auto_gen_var
        auto_gen_var = BooleanVar()
        auto_gen = Checkbutton(test_assembly_frame, text="Smart Location", variable=auto_gen_var, onvalue=True, offvalue=False)
        auto_gen.deselect()

        auto_gen.grid(row=4, column=0, columnspan=2)

        # Create assembly button
        initiate_btn = Button(test_assembly_frame, text="Initiate System", font=ft_button,\
                            padx=5, pady=5, borderwidth=4, command=self.initiate_sys)
        start_test_btn = Button(test_assembly_frame, text="Start Testing!", font=ft_button,\
                            padx=5, pady=5, borderwidth=4, command=self.config_test_assembly)
        exit = Button(self.test_assembly_config_window, text="Exit", font=ft_button,\
                padx=45, borderwidth=4, command=self.test_assembly_config_window.destroy)
        
        initiate_btn.grid(row=5, column=0, padx=5, pady=15)
        start_test_btn.grid(row=5, column=1, padx=5, pady=15)
        exit.grid(row=3, column=0, columnspan=2, padx=10, pady=25)

        self.test_assembly_config_window.mainloop()
    
    def config_test_assembly(self):
        # Get and check the passed value
        self.testmode = self.test_mode_input.get()
        self.component = self.test_component.get().lower()
        try:
            self.test_start_number = int(self.test_start_number_input.get())
            self.test_end_number = int(self.test_end_number_input.get())
        except ValueError:
            self.test_start_number_input.delete(0, END)
            self.test_end_number_input.delete(0, END)
            messagebox.showerror("Input Error", "Only positive integers are accepted!")
        else:
            if self.test_start_number <= 0 or self.test_start_number > 64 or self.test_end_number <= 0 or self.test_end_number > 64:
                messagebox.showerror("Input Error", "Input Numbers are out of range (1-64)!")
                self.test_start_number_input.delete(0, END)
                self.test_end_number_input.delete(0, END)
            elif self.test_end_number < self.test_start_number:
                messagebox.showerror("Input Error", "Starting number must be higher than ending number!")
                self.test_start_number_input.delete(0, END)
                self.test_end_number_input.delete(0, END)
            elif self._assembly_sys_is_online is True:
                self.current_nr = self.test_start_number
                self.init_asemb_test_gui()
            else:
                messagebox.showerror("Error!", "Initiate System first!")
            
    def init_asemb_test_gui(self):
        os.chdir(f"{PATH}\images")
        self.test_assembly_config_window.state(newstate='iconic')
        self.test_aseembly_run_window = Toplevel()
        self.test_aseembly_run_window.title("Running Assembly Test")
        self.test_aseembly_run_window.iconbitmap("Robotarm.ico")
        self.test_aseembly_run_window.geometry("535x350")

        # Create status bar
        self.test_asemb_status = StringVar()
        status_label = Label(self.test_aseembly_run_window, textvariable=self.test_asemb_status, font=ft_label, pady=10, bd=1, relief=SUNKEN)
        status_label.grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky=W+E)

        # Creat frame
        self.test_asemb_frame = LabelFrame(self.test_aseembly_run_window, padx=10, pady=10, borderwidth=5)
        self.test_asemb_frame.grid(row=1, column=0, padx=20, pady=5)

        # Create stop buttons
        self.grab_btn = Button(self.test_asemb_frame, text="Grab", padx=18, pady=5, borderwidth=4, command=self.asemb_test_gui_sub_grab)
        self.drop_btn = Button(self.test_asemb_frame, text="Drop", padx=17, pady=5, borderwidth=4, command=self.asemb_test_gui_sub_drop)
        self.home_btn = Button(self.test_asemb_frame, text="Home", padx=35, pady=5, borderwidth=4, command=self.go_home)
        self.save_btn = Button(self.test_asemb_frame, text="Save", padx=38, pady=5, borderwidth=4, command=self.save_position)
        self.free_move_btn = Button(self.test_asemb_frame, text="Free-move", font=ft_button, pady=15, borderwidth=4, command=self.free_move)
        self.left_btn = Button(self.test_asemb_frame, image=arrow_left, padx=10, pady=40, border=5, borderwidth=4, command=self.asemb_test_gui_back, state=DISABLED)
        self.right_btn = Button(self.test_asemb_frame, image=arrow_right, padx=10, pady=40, border=5, borderwidth=4, command=self.asemb_test_gui_next)
        
        self.left_btn.grid(row=0, column=0, padx=50)
        self.free_move_btn.grid(row=0, column=1)
        self.grab_btn.grid(row=1, column=0, pady=20)
        self.home_btn.grid(row=1, column=1)
        self.save_btn.grid(row=2, column=1)
        self.drop_btn.grid(row=1, column=2, pady=20)
        self.right_btn.grid(row=0, column=2, padx=50)

        exit = Button(self.test_aseembly_run_window, text="Exit", padx=45, borderwidth=4, command=self.exit_test_asemb)
        exit.grid(row=2, column=0, padx=10, pady=10)

        if self.testmode != 'both':
            self.test_asemb_status.set(f"Ready to test the [{self.current_nr}]th {self.component}'s {self.testmode.capitalize()} Position")
            self.grab_btn['state'] = 'disabled'
            self.drop_btn['state'] = 'disabled'
        else:
            self.testmode = 'sub_grab'
            self.test_asemb_status.set(f"Ready to test the [{self.current_nr}]th {self.component}'s Grab Position")
            self.grab_btn['state'] = 'disabled'
        
        self.asemb_test_rob_thread()
    
    def exit_test_asemb(self):
        self.test_aseembly_run_window.destroy()
        self.test_assembly_config_window.state(newstate='normal')
    
    def asemb_test_gui_sub_grab(self):
        self.grab_btn['state'] = 'disabled'
        self.drop_btn.config(text='Drop', command=self.asemb_test_gui_sub_drop, state=NORMAL)
        self.testmode = 'sub_grab'
        self.asemb_test_rob_thread()

    def asemb_test_gui_sub_drop(self):
        self.grab_btn['state'] = 'normal'
        self.drop_btn.config(text='Done', command=self.asemb_test_gui_sub_done)
        self.testmode = 'sub_drop'
        self.asemb_test_rob_thread()

    def asemb_test_gui_sub_done(self):
        self.drop_btn.config(text='Drop', command=self.asemb_test_gui_sub_drop, state=DISABLED)
        self.testmode = 'sub_done'
        self.asemb_test_rob_thread()

    def asemb_test_gui_next(self):
        if not self.testmode in ['grab', 'drop']:
            self.grab_btn['state'] = 'disabled'
            self.drop_btn['state'] = 'normal'
            self.testmode = 'sub_grab'
        self.current_nr += 1
        if self.current_nr == self.test_end_number:
            self.left_btn['state'] = 'normal'
            self.right_btn['state'] = 'disabled'
        elif self.current_nr == self.test_start_number and self.current_nr == self.test_end_number:
            self.right_btn['state'] = 'disabled'
            self.left_btn['state'] = 'disabled'  
        else:
            self.left_btn['state'] = 'normal'
            self.right_btn['state'] = 'normal'
        self.asemb_test_rob_thread()

    def asemb_test_gui_back(self):
        if not self.testmode in ['grab', 'drop']:
            self.grab_btn['state'] = 'disabled' 
            self.drop_btn['state'] = 'normal'
            self.testmode = 'sub_grab'
        self.current_nr -= 1
        if self.current_nr == self.test_start_number:
            self.right_btn['state'] = 'normal'
            self.left_btn['state'] = 'disabled'
        elif self.current_nr == self.test_start_number and self.current_nr == self.test_end_number:
            self.right_btn['state'] = 'disabled'
            self.left_btn['state'] = 'disabled'   
        else:
            self.left_btn['state'] = 'normal'
            self.right_btn['state'] = 'normal'
        self.asemb_test_rob_thread()

    def check_asemb_test_exe(self):
        if not self.asemb_test_rob_exe.is_alive():
            self.test_asemb_status.set(f"Ready to test the [{self.current_nr}]th {self.component}'s {self.testmode.capitalize()} Position")
            self.free_move_btn['state'] = 'normal'
            self.home_btn['state'] = 'normal'
            if self.testmode == 'sub_done':
                self.test_asemb_status.set(f"[{self.current_nr}]th {self.component}'s Positions have been done testing, restart or jump to next cell")
        else:
            self.test_asemb_status.set("Robot is now Moving, Please Wait...")
            self.test_aseembly_run_window.after(100, self.check_asemb_test_exe)

    def asemb_test_rob_thread(self):
        self.asemb_test_rob_exe = threading.Thread(target=self.asemb_test_rob)
        self.asemb_test_rob_exe.setDaemon(True)
        self.asemb_test_rob_exe.start()
        self.check_asemb_test_exe()

#----------------------Saving functions----------------------

    def save_position(self):
        os.chdir(f"{PATH}\data")
        if self.testmode == 'grab':
            rail_po = self.getPosition()
            grab_po = list(self.GetPose())
            self.parameter[self.component]['grabPo'][str(self.current_nr)] = grab_po
            if self.component == 'anode spacer':
                self.parameter['cathode spacer']['grabPo'][str(self.current_nr)] = list((grab_po[0], grab_po[1], grab_po[2]-0.5, grab_po[3], grab_po[4], grab_po[5]))
                extra_msg = ' and [cathode spacer]'
            else:
                extra_msg = ''
            with open('calibration.json', 'w') as json_file:
                json.dump(self.parameter, json_file, indent=4)
            nf.log_print(f"Component [{self.component}]{extra_msg} Nr.[{self.current_nr}]'s grab position has been updated- RailPO: [{rail_po}]; GrabPO: {grab_po}", logfile='calibrate') 
            self.test_asemb_status.set(f"Grab Position(s) of {self.component}{extra_msg} No.[{self.current_nr}] has been saved: {grab_po}")
        elif self.testmode == 'drop':
            drop_po = list(self.GetPose())
            self.parameter[self.component]['dropPo'][str(self.current_nr)] = drop_po
            if self.component == 'anode spacer':
                self.parameter['cathode spacer']['dropPo'][str(self.current_nr)] = drop_po
                extra_msg = ' and [cathode spacer]'
            else:
                extra_msg = ''
            with open('calibration.json', 'w') as json_file:
                json.dump(self.parameter, json_file, indent=4)
            nf.log_print(f"Component [{self.component}]{extra_msg} Nr.[{self.current_nr}]'s drop position has been updated: {drop_po}", logfile='calibrate')
            self.test_asemb_status.set(f"Drop Position(s) of {self.component}{extra_msg} No.[{self.current_nr}] has been saved: {drop_po}")
        elif self.testmode == 'sub_grab':
            rail_po = self.getPosition()
            grab_po = list(self.GetPose())
            self.parameter[self.component]['grabPo'][str(self.current_nr)] = grab_po
            if self.component == 'anode spacer':
                self.parameter['cathode spacer']['grabPo'][str(self.current_nr)] = list((grab_po[0], grab_po[1], grab_po[2]-0.5, grab_po[3], grab_po[4], grab_po[5]))
                extra_msg = ' and [cathode spacer]'
            else:
                extra_msg = ''
            with open('calibration.json', 'w') as json_file:
                json.dump(self.parameter, json_file, indent=4)
            nf.log_print(f"Component [{self.component}]{extra_msg} Nr.[{self.current_nr}]'s grab position has been updated- RailPO: [{rail_po}]; GrabPO: {grab_po}", logfile='calibrate')
            self.test_asemb_status.set(f"Grab Position(s) of {self.component}{extra_msg} No.[{self.current_nr}] has been saved: {grab_po}")
        elif self.testmode == 'sub_drop':
            drop_po = list(self.GetPose())
            self.parameter[self.component]['dropPo'][str(self.current_nr)] = drop_po
            if self.component == 'anode spacer':
                self.parameter['cathode spacer']['dropPo'][str(self.current_nr)] = drop_po
                extra_msg = ' and [cathode spacer]'
            else:
                extra_msg = ''
            with open('calibration.json', 'w') as json_file:
                json.dump(self.parameter, json_file, indent=4)
            nf.log_print(f"Component [{self.component}]{extra_msg} Nr.[{self.current_nr}]'s drop position has been updated: {drop_po}", logfile='calibrate')
            self.test_asemb_status.set(f"Drop Position(s) of {self.component}{extra_msg} No.[{self.current_nr}] has been saved: {drop_po}")
            
class TestTransportRobot(TransportRobot):
    def __init__(self):
        TransportRobot.__init__(self)
        self.constant = self.load_parameter()
        self._trans_rob_online = None
    
#----------------------Config functions----------------------

    def load_parameter(self):
        os.chdir(f"{PATH}\data")
        with open('calibration.json', 'r') as json_file:
            parameter = json.load(json_file)
        return parameter
    
    def write_parameter(self):
        os.chdir(f"{PATH}\data")
        with open('calibration.json', 'w') as json_file:
            json.dump(self.constant, json_file, indent=4)

#----------------------Motion functions----------------------

    def grip_test(self):
        ak_p = list(self.GetPose())
        self.GripperClose()
        time.sleep(1)
        self.MoveLin(ak_p[0], ak_p[1], ak_p[2]+35, ak_p[3], ak_p[4], ak_p[5])
        time.sleep(2)
        self.MoveLin(*ak_p)
        self.GripperOpen()

    def free_move_rob(self, axis, step):
        if axis == '+x':
            self.MoveLinRelWRF(abs(step),0,0,0,0,0)
        elif axis == '-x':
            self.MoveLinRelWRF(-abs(step),0,0,0,0,0)
        elif axis == '+y':
            self.MoveLinRelWRF(0,abs(step),0,0,0,0)
        elif axis == '-y':
            self.MoveLinRelWRF(0,-abs(step),0,0,0,0)
        elif axis == '+z':
            self.MoveLinRelWRF(0,0,abs(step),0,0,0)
        elif axis == '-z':
            self.MoveLinRelWRF(0,0,-abs(step),0,0,0)
        elif axis == 'rx':
            self.MoveLinRelWRF(0,0,0,step,0,0)
        elif axis == 'ry':
            self.MoveLinRelWRF(0,0,0,0,step,0)
        elif axis == 'rz':
            self.MoveLinRelWRF(0,0,0,0,0,step)
        elif axis == '+gripper':
            self.GripperOpen()
        elif axis == '-gripper':
            self.GripperClose()

    def trans_test_move_rob(self, testmode, back:bool):
        if testmode == 'Start Menu':
            self.go_home()
        elif testmode == 'Aligning Test' and back is True:
            self.MoveLin(*self.constant['GRIP_1_PO'])
            self.MoveJoints(*self.constant['WAIT_2_J'])
            self.SetTRF(*TCP_CP)
            self.MovePose(*self.constant['ALIGN_1_PO'])

            # Gripper goes down to position
            self.GripperOpen()
            time.sleep(0.5)
            self.MoveLin(*self.constant['ALIGN_2_PO'])
        elif testmode == 'Aligning Test' and back is False:
            nf.log_print("Calibrating aligning procedure...", logfile='calibrate')
            self.go_home()
            time.sleep(1)

            self.SetTRF(*TCP_CP)
            self.MoveJoints(*self.constant['WAIT_2_J'])
            self.MovePose(*self.constant['ALIGN_1_PO'])

            # Gripper goes down to position
            self.GripperOpen()
            time.sleep(0.5)
            self.MoveLin(*self.constant['ALIGN_2_PO'])
        elif testmode == 'Grabing Test' and back is True:
            self.MoveLinRelWRF(0,-80,0,0,0,0)
            self.MoveJoints(*self.constant['TRANS_1_J'])
            self.MoveJoints(*self.constant['ROTATE_RIGHT_J'])
            self.MoveJoints(*self.constant['ROTATE_LEFT_J'])
            # To the start posiiton
            self.SetTRF(*TCP_CP_180)
            self.MoveJoints(*self.constant['WAIT_2_J'])
            self.MovePose(*self.constant['GRIP_1_PO'])

            # Gripper goes down to position
            time.sleep(0.5)
            self.MoveLin(*self.constant['GRIP_2_PO'])
            self.GripperOpen()
        elif testmode == 'Grabing Test' and back is False:
            # Gripper goes up
            self.MoveLin(*self.constant['ALIGN_1_PO'])
            # To the start posiiton
            self.SetTRF(*TCP_CP_180)
            self.MoveJoints(*self.constant['WAIT_2_J'])
            self.MovePose(*self.constant['GRIP_1_PO'])

            # Gripper goes down to position
            self.GripperOpen()
            time.sleep(0.5)
            self.MoveLin(*self.constant['GRIP_2_PO'])
        elif testmode == 'Transporting Test' and back is True:
            self.MoveLin(*self.constant['TRANS_2_PO'])
        elif testmode == 'Transporting Test' and back is False:
            self.GripperClose()
            time.sleep(1)

            # Gripper goes up
            self.MoveLin(*self.constant['GRIP_1_PO'])

            # Set TCP back to normal
            self.SetTRF(*TCP_CP)

            # Reduce the rotating radius, rotate to crimper
            self.MoveJoints(*self.constant['ROTATE_LEFT_J'])
            self.MoveJoints(*self.constant['ROTATE_RIGHT_J'])

            # Drive through sigularity, ready to reach in
            self.MoveJoints(*self.constant['TRANS_1_J'])
            time.sleep(0.5)

            # Reaching into crimper next to the die:
            self.MoveLin(*self.constant['TRANS_2_PO'])
        elif testmode== 'Retrieving Test' and back is True:
            self.MoveLinRelWRF(0,0,-0.5,0,0,0)
            self.MoveLinRelWRF(-40,0,0,0,0,0)
            self.MoveLin(*self.constant['TRANS_2_PO'])
            self.MoveLin(*self.constant['BACKOFF_2_PO'])
            self.MoveLin(*self.constant['BACKOFF_1_PO'])
            self.MoveLin(*self.constant['TRANS_3_PO'])
        elif testmode== 'Retrieving Test' and back is False:
            self.MoveLin(*self.constant['TRANS_3_PO'])
        elif testmode =='Picking-up Test' and back is True:
            self.MoveLin(*self.constant['RETRIVE_6_PO'])
            self.MoveJoints(*self.constant['ROTATE_LEFT_J'])
            self.MoveJoints(*self.constant['ROTATE_RIGHT_J'])
            self.MovePose(*self.constant['RETRIVE_5_PO'])
            self.MoveLin(*self.constant['RETRIVE_4_PO'])
            self.MoveLin(*self.constant['RETRIVE_3_PO'])
        elif testmode =='Picking-up Test' and back is False:
            self.GripperOpen()
            time.sleep(0.5)

            # Move the gripper away from die
            self.MoveLin(*self.constant['BACKOFF_1_PO'])
            self.MoveLin(*self.constant['BACKOFF_2_PO'])
            self.MoveLin(*self.constant['BACKOFF_3_PO'])

            # Move out from crimper, goes to waitng position, ready to use the magenetic part
            self.MoveJoints(*self.constant['RETRIVE_1_J'])
            time.sleep(1)

            # Set TCP to normal:
            self.SetTRF(*TCP_CP)
            
            # Magnet reaching into the crimper next to the die:
            self.MoveLin(*self.constant['RETRIVE_2_PO'])

            # Above the die, magnetic Grabing:
            self.MoveLin(*self.constant['RETRIVE_3_PO'])
        elif testmode == 'Sliding Test' and back is True:
            self.MoveJoints(*self.constant['WAIT_2_J'])
            self.MovePose(*self.constant['RETRIVE_6_PO'])
            self.MoveLin(*self.constant['RETRIVE_7_PO'])
        elif testmode == 'Sliding Test' and back is False:
            # Move up 3 mm:
            self.MoveLin(*self.constant['RETRIVE_4_PO'])

            # Move the Magnet with CC away from die: Backwards
            self.MoveLin(*self.constant['RETRIVE_5_PO'])

            # Move to the ROTATION_RIGHT:
            self.MoveJoints(*self.constant['ROTATE_RIGHT_J'])

            # Move to the ROTATION_LEFT:
            self.MoveJoints(*self.constant['ROTATE_LEFT_J'])

            # Ready to drop the CC on Post::
            self.MovePose(*self.constant['RETRIVE_6_PO'])

            # Drop CC on the Post:
            self.MoveLin(*self.constant['RETRIVE_7_PO'])
        elif testmode == 'Done Test':
            # Perform Sliding:
            self.MoveLin(*self.constant['RETRIVE_8_PO'])

            # Move up, home the position
            self.MoveLinRelWRF(0,0,15,0,0,0)
            self.MoveJoints(*self.constant['WAIT_2_J'])
            self.MoveJoints(*self.constant['WAIT_1_J'])
        elif testmode == 'Home':
            self.go_home()
        elif testmode == 'Gripper Test':
            self.grip_test()
        elif testmode == 'Initiate':
            self.initiate_robot()
            res = self.GetStatusRobot()
            self._trans_rob_online = (res['Activated'], res['Homing']) == (1, 1)

    def end_trans_test(self):
        return self.disconnect_robot()

#----------------------GUI functions----------------------

    def free_move(self):
        os.chdir(f"{PATH}\images")
        self.test_transport_window.state(newstate='iconic')
        self.free_move_window = Toplevel()

        # Specify font of labels and button's text
        self.ft_label = font.Font(family='Arial', size=15, weight=font.BOLD)
        self.ft_button = font.Font(size=15)

        # Set the title, icon, size of the initial window
        self.free_move_window.title("Freemove GUI")
        self.free_move_window.iconbitmap("Robotarm.ico")
        self.free_move_window.geometry("830x660")

        # Create status bar
        self.free_move_status = StringVar()
        self.status = Label(self.free_move_window, textvariable=self.free_move_status, font=self.ft_label, pady=10, bd=1, relief=SUNKEN, anchor=W)
        self.status.grid(row=0, column=0, columnspan=2, padx=20, sticky=W+E)
        self.free_move_status.set(f"Current Location: {self.GetPose()}")

        # Create the control panel
        free_move_frame = LabelFrame(self.free_move_window, text="Movement Control Panel",\
            padx=25, pady=10, borderwidth=5)
        free_move_frame.grid(row=1, column=0, padx=20, pady=10)

        # Add input box for increment to functional Panel
        free_move_frame_increm = LabelFrame(free_move_frame, text="Increment: ",\
            font=self.ft_label, pady=8, borderwidth=3)
        self.increment = Entry(free_move_frame_increm, width=5, borderwidth=5)
        unit = Label(free_move_frame_increm, text="mm", font=self.ft_label)

        free_move_frame_increm.grid(row=0, column=0, padx=10, pady=5)
        self.increment.grid(row=0, column=0)
        unit.grid(row=0, column=1)

        self.increment.insert(0, '0.2')

        free_move_frame_rxyz = LabelFrame(free_move_frame, text="α-β-γ-Axis: ",\
            font=self.ft_label, padx=35, borderwidth=3)
        free_move_frame_rxyz.grid(row=0, column=1)

        free_move_frame_z = LabelFrame(free_move_frame, text="Z-Axis: ",\
            font=self.ft_label, padx=10, pady=30, borderwidth=3)
        free_move_frame_z.grid(row=1, column=0, padx=10, pady=10)

        free_move_frame_xy = LabelFrame(free_move_frame, text="XY-Axis: ",\
            font=self.ft_label, padx=20, pady=30, borderwidth=3)
        free_move_frame_xy.grid(row=1, column=1, padx=10, pady=10)

        free_move_frame_rail = LabelFrame(free_move_frame, text="Rail X-Axis: ",\
            font=self.ft_label, padx=88, borderwidth=3)
        free_move_frame_rail.grid(row=2, column=0, columnspan=2)

        # Add buttons to the control panel
        up_btn = Button(free_move_frame_z, image=arrow_up, padx=10, pady=40, border=5,\
            borderwidth=4, command=lambda: self.free_move_control('+z'))
        down_btn = Button(free_move_frame_z, image=arrow_down, padx=10, pady=40,\
            border=5, borderwidth=4, command=lambda: self.free_move_control('-z'))
        left_btn = Button(free_move_frame_xy, image=arrow_left, padx=10, pady=40,\
            border=5, borderwidth=4, command=lambda: self.free_move_control('-y'))
        right_btn = Button(free_move_frame_xy, image=arrow_right, padx=10, pady=40,\
            border=5, borderwidth=4, command=lambda: self.free_move_control('+y'))
        forward_btn = Button(free_move_frame_xy, image=arrow_up, padx=10, pady=40,\
            border=5, borderwidth=4, command=lambda: self.free_move_control('-x'))
        backward_btn = Button(free_move_frame_xy, image=arrow_down, padx=10, pady=40,\
            border=5, borderwidth=4, command=lambda: self.free_move_control('+x'))
        
        centrer_label_1 = Label(free_move_frame_z, image=centrer, padx=10, pady=40,\
            border=5, state=DISABLED)
        centrer_label_2 = Label(free_move_frame_xy, image=centrer, padx=10, pady=40,\
            border=5, state=DISABLED)

        rx_btn = Button(free_move_frame_rxyz, text="Δα", font=self.ft_button,\
            border=5, borderwidth=4, command=lambda: self.free_move_control('rx'))
        ry_btn = Button(free_move_frame_rxyz, text="Δβ", font=self.ft_button, border=5,\
            borderwidth=4, command=lambda: self.free_move_control('ry'))
        rz_btn = Button(free_move_frame_rxyz, text="Δγ", font=self.ft_button, border=5,\
            borderwidth=4, command=lambda: self.free_move_control('rz'))
        rail_poitive_btn = Button(free_move_frame_rail, image=arrow_right, border=5,\
            borderwidth=4, state=DISABLED)
        rail_negative_btn = Button(free_move_frame_rail, image=arrow_left, border=5,\
            borderwidth=4, state=DISABLED)

        up_btn.grid(row=0, column=0, padx=10)
        down_btn.grid(row=2, column=0, padx=10)
        centrer_label_1.grid(row=1, column=0)
        left_btn.grid(row=1, column=0)
        right_btn.grid(row=1, column=2)
        forward_btn.grid(row=0, column=1)
        backward_btn.grid(row=2, column=1)
        centrer_label_2.grid(row=1, column=1)
        rx_btn.grid(row=0, column=0, padx=10)
        ry_btn.grid(row=0, column=1, padx=10)
        rz_btn.grid(row=0, column=2, padx=10)
        rail_negative_btn.grid(row=0, column=0, padx=20)
        rail_poitive_btn.grid(row=0, column=1, padx=20)

        # Create Functional Frame
        function_frame = LabelFrame(self.free_move_window, text="Function Control Panel",\
            padx=25, pady=7, borderwidth=5)
        function_frame.grid(row=1, column=1, padx=5, pady=20)

        gripper_control_frame = LabelFrame(function_frame, text="Gripper Control",\
            padx=30, pady=10, borderwidth=5)
        gripper_control_frame.grid(row=0, column=0, padx=5, pady=5)

        vacuum_control_frame = LabelFrame(function_frame, text="Vacuum Control",\
            padx=30, pady=10, borderwidth=5)
        vacuum_control_frame.grid(row=1, column=0, padx=5, pady=5)

        position_control_frame = LabelFrame(function_frame, text="Position Control",\
            padx=30, pady=10, borderwidth=5)
        position_control_frame.grid(row=2, column=0, padx=5, pady=5)

        # Add functional buttons to the functional panel
        global open_gripper_btn, close_gripper_btn, open_vacuum_btn, close_vacuum_btn
        open_gripper_btn = Button(gripper_control_frame, text="Open Gripper",\
            border=5, padx=24, pady=10, borderwidth=4, command=lambda: self.free_move_control('+gripper'))
        close_gripper_btn = Button(gripper_control_frame, text="Close Gripper",\
            padx=24, pady=10, border=5, borderwidth=4, command=lambda: self.free_move_control('-gripper'))
        open_vacuum_btn = Button(vacuum_control_frame, text="Open Vacuum",\
            padx=20, pady=10, border=5, borderwidth=4, state=DISABLED)
        close_vacuum_btn = Button(vacuum_control_frame, text="Close Vacuum",\
            padx=20, pady=10, border=5, borderwidth=4, state=DISABLED)
        test_btn = Button(position_control_frame, text="Test Position",\
            padx=25, pady=10, border=5, borderwidth=4, state=DISABLED)
        save_btn = Button(position_control_frame, text="Save Position",\
            padx=23, pady=10, border=5, borderwidth=4, state=DISABLED)
        exit_btn = Button(position_control_frame, text="Exit",\
            padx=48, pady=10, borderwidth=4, command=self.exit_free_move)

        open_gripper_btn.grid(row=0, column=0)
        close_gripper_btn.grid(row=1, column=0, pady=5)
        open_vacuum_btn.grid(row=0, column=0)
        close_vacuum_btn.grid(row=1, column=0, pady=5)
        test_btn.grid(row=0, column=0)
        save_btn.grid(row=1, column=0, pady=5)
        exit_btn.grid(row=2, column=0)

        self.free_move_window.mainloop()

    def exit_free_move(self):
        self.free_move_window.destroy()
        self.test_transport_window.state(newstate='normal')

    def check_free_move_exe(self):
        if not self.free_move_exe.is_alive():
            self.free_move_status.set(f"Current Location: {self.GetPose()}")
        else:
            self.free_move_status.set("Robot is now Moving, Please Wait...")
            self.free_move_window.after(100, self.check_free_move_exe)
    
    def free_move_rob_thread(self, axis, step):
        self.free_move_exe = threading.Thread(target=self.free_move_rob, args=[axis, step])
        self.free_move_exe.setDaemon(True)
        self.free_move_exe.start()
        self.check_free_move_exe()

    def free_move_control(self, axis):
        try:
            step = float(self.increment.get())
        except ValueError:
            messagebox.showerror("Input Error!", "Only positive float is accepted")
        else:
            if axis == '+gripper':
                open_gripper_btn['state'] = 'disable'
                close_gripper_btn['state'] = 'normal'
            elif axis == '-gripper':
                open_gripper_btn['state'] = 'normal'
                close_gripper_btn['state'] = 'disable'
            self.free_move_rob_thread(axis, step)

    def init_trans_test_gui(self):
        self.testmode = 'Start Menu'

        os.chdir(f"{PATH}\images")
        # Start a new window
        self.test_transport_window = Toplevel()
        self.test_transport_window.title("Transport Robot Testing Interface")
        self.test_transport_window.iconbitmap("Robotarm.ico")
        self.test_transport_window.geometry("420x320")

        # Load images
        global arrow_left, arrow_right, arrow_up, arrow_down, centrer, done
        arrow_left = ImageTk.PhotoImage(Image.open("arrow_left.png"))
        arrow_right = ImageTk.PhotoImage(Image.open("arrow_right.png"))
        arrow_up = ImageTk.PhotoImage(Image.open("arrow_up.png"))
        arrow_down = ImageTk.PhotoImage(Image.open("arrow_down.png"))
        centrer = ImageTk.PhotoImage(Image.open("centrer.png"))
        done = ImageTk.PhotoImage(Image.open("done.png"))

        # Specify font of labels and button's text
        global ft_label, ft_button
        ft_label = font.Font(family='Arial', size=10, weight=font.BOLD)
        ft_button = font.Font(size=15)

        # Create status bar
        self.status_str = StringVar()
        status_label = Label(self.test_transport_window, textvariable=self.status_str, font=ft_label, pady=10, bd=1, relief=SUNKEN)
        status_label.grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky=W+E)
        self.status_str.set("Start Menu")

        # Creat frame
        self.test_transport_frame = LabelFrame(self.test_transport_window, padx=10, pady=10, borderwidth=5)
        self.test_transport_frame.grid(row=1, column=0, padx=20, pady=5)

        # Creat labels
        intro_1 = Label(self.test_transport_frame,\
                    text="Place the testing cell on Post,\nThen Press [Start] when ready: ")

        intro_1.grid(row=0, column=0, columnspan=3)

        # Create start buttons
        global start_test_btn, home_btn, load_btn
        start_test_btn = Button(self.test_transport_frame, text="Start", font=ft_button,\
                        padx=15, pady=15, borderwidth=4, command=self.start_trans_test, state=DISABLED)
        start_test_btn.grid(row=1, column=0, padx=10, pady=10)
        home_btn = Button(self.test_transport_frame, text="Home", font=ft_button,\
                    padx=15, pady=15, borderwidth=4, command=lambda: self.trans_test_rob_thread('Home'), state=DISABLED)
        home_btn.grid(row=1, column=1, padx=10, pady=10)
        load_btn = Button(self.test_transport_frame, text="Initiate", font=ft_button,\
                    padx=15, pady=15, borderwidth=4, command=self.initiate_test)
        load_btn.grid(row=1, column=2, padx=10, pady=10)

        # Greate exit button
        exit = Button(self.test_transport_window, text="Exit", font=ft_button,\
                padx=45, pady=5, borderwidth=4, command=self.test_transport_window.destroy)
        exit.grid(row=2, column=0, padx=10, pady=10)

        self.test_transport_window.mainloop()
    
    def initiate_test(self):

        os.chdir(f"{PATH}\images")
        prog_window = Toplevel()
        prog_window.title("Transport Robot initializing")
        prog_window.iconbitmap("Robotarm.ico")
        prog_window.geometry('280x150')
        prog_text = StringVar()
        prog_label = Label(prog_window, textvariable=prog_text, font=ft_label, pady=10, anchor=CENTER)
        prog = ttk.Progressbar(prog_window, length=250, mode='determinate', orient=HORIZONTAL)
        prog_label.grid(row=2, column=0, columnspan=2)
        prog.grid(row=1, column=0, columnspan=2, pady=20, sticky=W+E)
        self.trans_test_rob_thread('Initiate')
        prog.start(300)
        while True:
            prog_text.set(f"Initiating System, Please Wait ({prog['value']}%)")
            prog_window.update()
            if not self.rob_thread.is_alive():
                prog.stop()
                prog['value'] = 100
                prog_text.set(f"Initiating System, Please Wait ({prog['value']}%)")
                prog_window.update()
                time.sleep(1)
                prog_window.destroy()
                if self._trans_rob_online is True:
                    start_test_btn['state'] = 'normal'
                    home_btn['state'] = 'normal'
                break
        prog_window.mainloop()

    def start_trans_test(self):
        if self._trans_rob_online is True:
            self.trans_test_gui('Aligning Test')
        else:
            messagebox.showerror('Connection Error', "Please Initiate System first!")
    
    def trans_test_gui(self, testmode:str, back:bool=False):
        run_txt = {
        'Start Menu': "Returning to the Start Position",
        'Aligning Test': "Changing to Aligning Position",
        'Grabing Test': "Changing to Grabing Position",
        'Transporting Test': "Changing to Transporting Position",
        'Retrieving Test': "Changing Retrieving Position",
        'Picking-up Test': "Changing to Picking-Up Position",
        'Sliding Test': "Changing to Sliding Position",
        'Done Test': "Finishing Test, Returning to Homeing Position",
        'Home': "Homing Position",
        'Gripper Test': "Implementing Gripper Test",
        'Initiate': "Initiating"
        }

        test = ['Start Menu', 'Aligning Test', 'Grabing Test', 'Transporting Test', 'Retrieving Test', 'Picking-up Test', 'Sliding Test', 'Done Test']
        if testmode in test:
            self.testmode = testmode
            test_index = test.index(testmode)
            if testmode == 'Start Menu':
                # Clear pervious widget
                self.test_transport_window.geometry("420x320")
                for widget in self.test_transport_frame.winfo_children():
                    widget.destroy()
                
                # Creat labels
                intro_1 = Label(self.test_transport_frame,\
                            text="Place the testing cell on Tray: [7] Position: [64]\nwith cathode case facing upwards.\nClick [Start] when ready: ")
                intro_1.grid(row=0, column=0, columnspan=3)

                # Create start buttons
                start_test_btn = Button(self.test_transport_frame, text="Start", font=ft_button,\
                                padx=15, pady=15, borderwidth=4, command=lambda: self.trans_test_gui('Aligning Test'))
                start_test_btn.grid(row=1, column=0, padx=10, pady=10)
                home_btn = Button(self.test_transport_frame, text="Home", font=ft_button,\
                            padx=15, pady=15, borderwidth=4, command=lambda: self.trans_test_rob_thread('Home'))
                home_btn.grid(row=1, column=1, padx=10, pady=10)
                load_btn = Button(self.test_transport_frame, text="Initiate", font=ft_button,\
                            padx=15, pady=15, borderwidth=4, command=lambda: self.trans_test_rob_thread('Initiate'))
                load_btn.grid(row=1, column=2, padx=10, pady=10)
                if self._trans_rob_online is True:
                    start_test_btn['state'] = 'normal'
                    home_btn['state'] = 'normal'
                else:
                    start_test_btn['state'] = 'disabled'
                    home_btn['state'] = 'disabled'
            elif testmode == 'Aligning Test':
                # Clear pervious widget
                self.test_transport_window.geometry("500x340")
                for widget in self.test_transport_frame.winfo_children():
                    widget.destroy()

                # update status bar
                status_label = Label(self.test_transport_window, textvariable=self.status_str, font=ft_label,\
                                    pady=10, bd=1, relief=SUNKEN)
                status_label.grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky=W+E)

                # Greate other functional buttons
                self.home_btn = Button(self.test_transport_frame, text="Home",\
                            padx=10, pady=5, borderwidth=4, command=lambda: self.trans_test_gui('Start Menu'))
                self.test_btn = Button(self.test_transport_frame, text="Test", padx=20,\
                            pady=5, borderwidth=4, command=lambda: self.trans_test_rob_thread('Gripper Test'))
                self.free_move_btn = Button(self.test_transport_frame, text="Free-move",\
                                padx=5, pady=5, borderwidth=4, command=self.free_move)
                self.save_btn = Button(self.test_transport_frame, text="Save", font=ft_button,\
                            padx=10, pady=15, borderwidth=4, command=lambda: self.save_position(testmode))
                self.left_btn = Button(self.test_transport_frame, image=arrow_left, padx=10, pady=40, border=5, borderwidth=4, command=lambda: self.trans_test_gui('Start Menu'), state=DISABLED)
                self.right_btn = Button(self.test_transport_frame, image=arrow_right, padx=10, pady=40, border=5, borderwidth=4, command=lambda: self.trans_test_gui(test[test_index+1]), state=DISABLED)
                
                self.left_btn.grid(row=0, column=0, padx=50)
                self.save_btn.grid(row=0, column=1)
                self.home_btn.grid(row=1, column=0, pady=20)
                self.free_move_btn.grid(row=1, column=1, pady=20)
                self.test_btn.grid(row=1, column=2, pady=20)
                self.right_btn.grid(row=0, column=2, padx=50)

                self.status_str.set(f"Robot is now {run_txt[testmode]}, Please Wait...")
            elif testmode == 'Done Test':
                self.save_btn.config(state=DISABLED)
                self.left_btn.config(image=arrow_left, command=lambda: self.trans_test_gui(testmode='Sliding Test', back=True), state=DISABLED)
                self.right_btn.config(image=done, command=lambda: self.trans_test_gui('Start Menu'), state=DISABLED)
            else:
                self.status_str.set(f"Robot is now {run_txt[testmode]}, Please Wait...")
                self.save_btn.config(command=lambda: self.save_position(testmode))
                self.left_btn.config(image=arrow_left, command=lambda: self.trans_test_gui(testmode=test[test_index-1], back=True), state=DISABLED)
                self.right_btn.config(image=arrow_right, command=lambda: self.trans_test_gui(test[test_index+1]), state=DISABLED)
        
        # Robot execute simultanous movement    
        self.trans_test_rob_thread(testmode=testmode, back=back)

    def check_rob_thread(self, testmode):
        done_txt = {
        'Start Menu': "[Start Menu]",
        'Aligning Test': "[Aligning Test]",
        'Grabing Test': "[Grabing Test]",
        'Transporting Test': "[Transporting Test]",
        'Retrieving Test': "[Retrieving Test]",
        'Picking-up Test': "[Picking-Up Test]",
        'Sliding Test': "[Sliding Test]",
        'Done Test': "All Tests has been Done, Click [✓] to Return the testing cell",
        'Home': f"[{self.testmode}]: Homing Done",
        'Gripper Test': f"[{self.testmode}]: Gripper Test has been Done",
        'Initiate': f"[{self.testmode}]: System has been initiated"
        }
        if not self.rob_thread.is_alive():
            if self.testmode != 'Start Menu':
                self.left_btn['state'] = 'normal'
                self.right_btn['state'] = 'normal'
            self.status_str.set(done_txt[testmode])
        else:
            self.test_transport_window.after(100, lambda:self.check_rob_thread(testmode))
        
    def trans_test_rob_thread(self, testmode, back:bool=False):
        self.rob_thread = threading.Thread(target=self.trans_test_move_rob, args=[testmode, back])
        self.rob_thread.setDaemon(True)
        self.rob_thread.start()
        self.check_rob_thread(testmode=testmode)

#----------------------Saving functions----------------------

    def save_position(self, testmode):
        os.chdir(f"{PATH}\data")
        if testmode == 'Aligning Test':
            ak_po = list(self.GetPose())
            self.constant['ALIGN_2_PO'] = ak_po
            self.constant['ALIGN_1_PO'] = [ak_po[0], ak_po[1], ak_po[2]+35, ak_po[3], ak_po[4], ak_po[5]]
            self.write_parameter()
            nf.log_print(f"Positions have been updated:  ['ALIGN_1_PO']: {self.constant['ALIGN_1_PO']}", logfile='calibrate')
            nf.log_print(f"Positions have been updated:  ['ALIGN_2_PO']: {self.constant['ALIGN_2_PO']}", logfile='calibrate')
            messagebox.showinfo("Information", f"Positions have been updated:\
            \n['ALIGN_1_PO']: {self.constant['ALIGN_1_PO']}\
            \n['ALIGN_2_PO']: {self.constant['ALIGN_2_PO']}")
        elif testmode == 'Grabing Test':
            ak_po = list(self.GetPose())
            self.constant['GRIP_2_PO'] = ak_po
            self.constant['GRIP_1_PO'] = [ak_po[0], ak_po[1], ak_po[2]+85, ak_po[3], ak_po[4], ak_po[5]]
            self.write_parameter()
            nf.log_print(f"Positions have been updated:  ['GRIP_1_PO']: {self.constant['GRIP_1_PO']}", logfile='calibrate')
            nf.log_print(f"Positions have been updated:  ['GRIP_2_PO']: {self.constant['GRIP_2_PO']}", logfile='calibrate')
            messagebox.showinfo("Information", f"Positions have been updated:\
            \n['GRIP_1_PO']: {self.constant['GRIP_1_PO']}\
            \n['GRIP_2_PO']: {self.constant['GRIP_2_PO']}")
        elif testmode == 'Transporting Test':
            ak_po = list(self.GetPose())
            self.constant['TRANS_2_PO'] = ak_po
            self.write_parameter()
            nf.log_print(f"Position has been updated: ['TRANS_2_PO']: {self.constant['TRANS_2_PO']}", logfile='calibrate')
            messagebox.showinfo("Information", f"Positions have been updated:\
            \n['TRANS_2_PO']: {self.constant['TRANS_2_PO']}")
        elif testmode == 'Retrieving Test':
            ak_po = list(self.GetPose())
            self.constant['TRANS_3_PO'] = ak_po
            self.constant['BACKOFF_1_PO'] = [ak_po[0], ak_po[1]+18, ak_po[2], ak_po[3], ak_po[4], ak_po[5]]
            self.constant['BACKOFF_2_PO'] = [ak_po[0]-35, ak_po[1]+18, ak_po[2], ak_po[3], ak_po[4], ak_po[5]]
            self.constant['BACKOFF_3_PO'] = [ak_po[0]-35, ak_po[1]-79, ak_po[2], ak_po[3], ak_po[4], ak_po[5]]
            self.write_parameter()
            nf.log_print(f"Position has been updated: ['TRANS_3_PO']: {self.constant['TRANS_3_PO']}", logfile='calibrate')
            nf.log_print(f"Position has been updated: ['BACKOFF_1_PO']: {self.constant['BACKOFF_1_PO']}", logfile='calibrate')
            nf.log_print(f"Position has been updated: ['BACKOFF_2_PO']: {self.constant['BACKOFF_2_PO']}", logfile='calibrate')
            nf.log_print(f"Position has been updated: ['BACKOFF_3_PO']: {self.constant['BACKOFF_3_PO']}", logfile='calibrate')
            messagebox.showinfo("Information", f"Positions have been updated:\
            \n['TRANS_3_PO']: {self.constant['TRANS_3_PO']},\
            \n['BACKOFF_1_PO']: {self.constant['BACKOFF_1_PO']},\
            \n['BACKOFF_2_PO']: {self.constant['BACKOFF_2_PO']}:\
            \n['BACKOFF_3_PO']: {self.constant['BACKOFF_3_PO']}")
        elif testmode == 'Picking-up Test':
            ak_po = list(self.GetPose())
            self.constant['RETRIVE_3_PO'] = ak_po
            self.constant['RETRIVE_2_PO'] = [ak_po[0]-25, ak_po[1], ak_po[2], ak_po[3], ak_po[4], ak_po[5]]
            self.constant['RETRIVE_4_PO'] = [ak_po[0], ak_po[1], ak_po[2]+3, ak_po[3], ak_po[4], ak_po[5]]
            self.constant['RETRIVE_5_PO'] = [ak_po[0], ak_po[1]-60, ak_po[2]+3, ak_po[3], ak_po[4], ak_po[5]]
            self.write_parameter()
            nf.log_print(f"Position has been updated: ['RETRIVE_2_PO']: {self.constant['RETRIVE_2_PO']}", logfile='calibrate')
            nf.log_print(f"Position has been updated: ['RETRIVE_3_PO']: {self.constant['RETRIVE_3_PO']}", logfile='calibrate')
            nf.log_print(f"Position has been updated: ['RETRIVE_4_PO']: {self.constant['RETRIVE_4_PO']}", logfile='calibrate')
            nf.log_print(f"Position has been updated: ['RETRIVE_5_PO']: {self.constant['RETRIVE_5_PO']}", logfile='calibrate')
            messagebox.showinfo("Information", f"Positions have been updated:\
            \n['RETRIVE_2_PO']: {self.constant['RETRIVE_2_PO']},\
            \n['RETRIVE_3_PO']: {self.constant['RETRIVE_3_PO']},\
            \n['RETRIVE_4_PO']: {self.constant['RETRIVE_4_PO']}:\
            \n['RETRIVE_5_PO']: {self.constant['RETRIVE_5_PO']}")
        elif testmode == 'Sliding Test':
            ak_po = list(self.GetPose())
            self.constant['RETRIVE_7_PO'] = ak_po
            self.constant['RETRIVE_6_PO'] = [ak_po[0], ak_po[1], ak_po[2]+40, ak_po[3], ak_po[4], ak_po[5]]
            self.constant['RETRIVE_8_PO'] = [ak_po[0]+25, ak_po[1], ak_po[2], ak_po[3], ak_po[4], ak_po[5]]
            self.write_parameter()
            nf.log_print(f"Positions have been updated: ['RETRIVE_6_PO']: {self.constant['RETRIVE_6_PO']}", logfile='calibrate')
            nf.log_print(f"Positions have been updated: ['RETRIVE_7_PO']: {self.constant['RETRIVE_7_PO']}", logfile='calibrate')
            nf.log_print(f"Positions have been updated: ['RETRIVE_8_PO']: {self.constant['RETRIVE_7_PO']}", logfile='calibrate')
            messagebox.showinfo("Information", f"Positions have been updated:\
            \n['RETRIVE_6_PO']: {self.constant['RETRIVE_6_PO']},\
            \n['RETRIVE_7_PO']: {self.constant['RETRIVE_7_PO']},\
            \n['RETRIVE_8_PO']: {self.constant['RETRIVE_8_PO']}")

if __name__ == '__main__':
    os.chdir(PATH)
    ui = TestTransportRobot()
    ui.init_trans_test_gui()