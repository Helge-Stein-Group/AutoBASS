import json
import os
from tkinter import *
from tkinter import messagebox
import numpy as np
import math as ma
import notify as nf
PATH = os.path.dirname(__file__) # ..../config

COMPONENTS = ['cathode case', 'cathode spacer', 'cathode', 'separator', 'anode', 'anode spacer', 'spring', 'anode case']

class ResetParameter():

    def __init__(self):
        pass

    def start_config_gui(self):
        os.chdir(f"{PATH}\images")
        self.pos_config_window = Toplevel()
        # Set the title, icon, size of the initial window
        self.pos_config_window.title("AutoBASS Config")
        self.pos_config_window.iconbitmap("Location.ico")
        self.pos_config_window.geometry("345x680")

        config_frame = LabelFrame(self.pos_config_window, text="Configure Position:", padx=15, pady=20, borderwidth=5)
        config_frame.grid(row=0, column=0, padx=5, pady=10)

        generate_frame = LabelFrame(self.pos_config_window, text="Generate Position:", padx=10, pady=18, borderwidth=5)
        generate_frame.grid(row=0, column=1, padx=5, pady=10)

        setup_frame = LabelFrame(self.pos_config_window, text="General Setup:", padx=10, pady=20, borderwidth=5)
        setup_frame.grid(row=1, columnspan=2, padx=5)

        global user_confirm
        user_confirm = IntVar()
        user_confirm.set(1)

        #for text, mode in modes:
        calibration_rb = Radiobutton(config_frame, text='Calibrated Positions', variable=user_confirm, value=1)
        default_rb = Radiobutton(config_frame, text='Default Positions', variable=user_confirm, value=2)

        calibration_rb.pack(anchor=W)
        default_rb.pack(anchor=W)

        regenerate_btn= Button(generate_frame, text="Regenerate", font=('Arial', 10), padx=10, pady=10, border=5, borderwidth=4, command=self.auto_calib)
        reset_drop_btn = Button(generate_frame, text="Reset Drop", font=('Arial', 10), padx=11, pady=10, border=5, borderwidth=4, command=self.reset_drop_data)

        global apply_btn
        apply_btn = Button(config_frame, text="Apply", font=('Arial', 10), padx=40, pady=10, borderwidth=4, command=self.apply_data)
        exit_btn = Button(self.pos_config_window, text="OK", font=('Arial', 14), padx=40, borderwidth=4, command=self.confirm_setup)

        regenerate_btn.pack(padx=10, pady=10)
        reset_drop_btn.pack(padx=10)
        apply_btn.pack(pady=10)
        exit_btn.grid(row=3, column=0, pady=10, columnspan=2)

        global joint_vel_slider, cartlin_vel_slider, gripper_vel_slider, gripper_force_slider, axis_vel_slider, electrolyte_volume_slider
        joint_vel_slider = Scale(setup_frame, from_=30, to=80, length=300, label='Joint Velocity mm/s', orient=HORIZONTAL)
        cartlin_vel_slider = Scale(setup_frame, from_=10, to=50, length=300, label='CarLin Velocity mm/s', orient=HORIZONTAL)
        axis_vel_slider = Scale(setup_frame, from_=10, to=50, length=300, label='Axis Velocity mm/s', orient=HORIZONTAL)
        gripper_vel_slider = Scale(setup_frame, from_=10, to=100, length=300, label='Gripper Velocity %', orient=HORIZONTAL)
        gripper_force_slider = Scale(setup_frame, from_=10, to=100, length=300, label='Gripper Force %', orient=HORIZONTAL)
        electrolyte_volume_slider = Scale(setup_frame, from_=10, to=100, length=300, label='Electrolyte Volume µL', orient=HORIZONTAL)
        
        joint_vel_slider.grid(row=0, column=0)
        cartlin_vel_slider.grid(row=1, column=0)
        axis_vel_slider.grid(row=2, column=0)
        gripper_vel_slider.grid(row=3, column=0)
        gripper_force_slider.grid(row=4, column=0)
        electrolyte_volume_slider.grid(row=5, column=0)

        os.chdir(f"{PATH}\data")
        with open('config.json') as json_file:
            readings = json.load(json_file)
        joint_vel_slider.set(readings['J_VEL'])
        cartlin_vel_slider.set(readings['L_VEL'])
        gripper_vel_slider.set(readings['GRIP_VEL'])
        gripper_force_slider.set(readings['GRIP_F'])
        axis_vel_slider.set(readings['AX_VEL'])
        electrolyte_volume_slider.set(readings['ELECTROLYTE_VOL'])

        self.pos_config_window.mainloop()

    def apply_data(self):
        if user_confirm.get() == 1:
            self.resume_data()
        elif user_confirm.get() ==2:
            self.reset_data()

    def confirm_setup(self):
        os.chdir(f"{PATH}\data")
        with open('config.json') as json_file:
            readings = json.load(json_file)
        readings['J_VEL'] = joint_vel_slider.get()
        readings['L_VEL'] = cartlin_vel_slider.get()
        readings['GRIP_VEL'] = gripper_vel_slider.get()
        readings['GRIP_F'] = gripper_force_slider.get()
        readings['AX_VEL'] = axis_vel_slider.get()
        readings['ELECTROLYTE_VOL'] = electrolyte_volume_slider.get()
        with open('config.json', 'w') as outfile:
                json.dump(readings, outfile, indent=4)
        self.pos_config_window.destroy()
        
    def resume_data(self):
        os.chdir(f"{PATH}\data")
        # Apply calibrated positions
        with open('calibration.json') as json_file:
            readings = json.load(json_file)
        with open('config.json', 'w') as outfile:
                json.dump(readings, outfile, indent=4)
        nf.log_print("Calibrated Positions have been applied")
        messagebox.showinfo("New Positions Confirmed","Calibrated Positions have been applied!")
    
    def reset_data(self):
        os.chdir(f"{PATH}\data")
        # Apply default positions
        with open('default.json') as json_file:
                readings = json.load(json_file)
        with open('config.json', 'w') as outfile:
                    json.dump(readings, outfile, indent=4)
        nf.log_print("Default positions have been applied")
        messagebox.showinfo("New Positions Confirmed","Default Positions have been applied!")

    def auto_calib(self):
        os.chdir(f"{PATH}\data")
        with open('calibration.json') as json_file:
            readings = json.load(json_file)
        for component in COMPONENTS:
            ref_grab = readings[component]['grabPo']['1']
            ref_drop = readings[component]['dropPo']['1']
            for cell_nr in range(2, 65):
                gen_grab = ref_grab[:]
                gen_grab[1] -= (cell_nr-1)%8*23
                readings[component]['grabPo'][str(cell_nr)] = gen_grab
                readings[component]['dropPo'][str(cell_nr)] = ref_drop
        with open('default.json', 'w') as outfile:
                    json.dump(readings, outfile, indent=4)
        nf.log_print("New default data has been gennerated")
        messagebox.showinfo("New Positions Generated","Default Positions have been regenerated!")

    def gen_default_data(self, seed:int=1):
        os.chdir(f"{PATH}\data")
        # Seed is the coloum of which the position you want to asign as referance
        # Copy seed coloum's coordinate to the rest of coloums 
        # Copy anode spacers' x,y coordinates to cathode spacer, with subtracting 0.5mm on z-axis
        if seed >=8 or seed <= 0:
            raise ValueError
        else:
            with open('calibration.json') as json_file:
                readings = json.load(json_file)
            for component in COMPONENTS:
                for row in range(1,9):
                    ref_grab = readings[component]['grabPo'][str(row+(seed-1)*8)]
                    ref_drop = readings[component]['dropPo'][str(row+(seed-1)*8)]
                    for coloum in range(seed,8):
                        readings[component]['grabPo'][str(row+coloum*8)] = ref_grab
                        readings[component]['dropPo'][str(row+coloum*8)] = ref_drop
            for cell_nr in range(1,65):
                anode_spacer = readings['anode spacer']['grabPo'][str(cell_nr)]
                cathode_spacer = list((anode_spacer[0], anode_spacer[1], anode_spacer[2]-0.7, anode_spacer[3], anode_spacer[4], anode_spacer[5]))
                readings['cathode spacer']['grabPo'][str(cell_nr)] = cathode_spacer
            with open('default.json', 'w') as outfile:
                    json.dump(readings, outfile, indent=4)
            nf.log_print("New default data has been gennerated")

    def reset_drop_data(self):
        os.chdir(f"{PATH}\data")
        with open('calibration.json') as json_file:
            readings = json.load(json_file)
        for component in COMPONENTS:
            for cell_nr in range(1, 65):
                readings[component]['dropPo'][str(cell_nr)] = readings[component]['dropPo']['1']
        with open('config.json', 'w') as outfile:
                json.dump(readings, outfile, indent=4)
        nf.log_print("All drop positions have been reset to default")
        messagebox.showinfo("New Positions Generated","Default Drop-Positions have been regenerated!")

    def smart_calib_xy(self):
        os.chdir(f"{PATH}\data")
        with open('calibration.json') as json_file:
            readings = json.load(json_file)
        for component in COMPONENTS:
            xy_1 = readings[component]['grabPo']['1'][:2]
            xy_57 = readings[component]['grabPo']['57'][:2]
            theta = ma.atan((xy_57[1]-xy_1[1])/(xy_57[0]-xy_1[0]+23*7))
            transMatrx = np.array([[ma.cos(theta), -ma.sin(theta)],
                                [ma.sin(theta), ma.cos(theta)]])
            for cell_nr in range(2, 65):
                nominal_xy = [xy_1[0]+(cell_nr-1)/8*23, xy_1[1]-(cell_nr-1)%8*23]
                trans_xy = np.dot(transMatrx, nominal_xy)
                offset_xy = [trans_xy[0]-nominal_xy[0], trans_xy[1]-nominal_xy[1]]
                new_xy = [xy_1[0]+offset_xy[0], xy_1[1]-(cell_nr-1)%8*23+offset_xy[1]]
                readings[component]['grabPo'][str(cell_nr)][0] = new_xy[0]
                readings[component]['grabPo'][str(cell_nr)][1] = new_xy[1]
                readings[component]['grabPo'][str(cell_nr)][2] = readings[component]['grabPo']['1'][2]
                readings[component]['dropPo'][str(cell_nr)] = readings[component]['dropPo']['1']
        with open('default.json', 'w') as outfile:
                json.dump(readings, outfile, indent=4)
        nf.log_print("Smart calibration implemented")
        messagebox.showinfo("New Positions Generated","Smart calibration implemented, default Positions reseted!")
 
if __name__ == '__main__':
    os.chdir(PATH)
    pos_gen = ResetParameter()
    pos_gen.start_config_gui()