from tkinter import *
from tkinter import font
from tkinter import messagebox
from tkinter import ttk
import os
import time
import threading
import Assembly as asb
import Robot_test_UI as testrob
from Position_generator import ResetParameter

PATH = os.path.dirname(__file__)
 
class AutobassGUI(ResetParameter):
    def __init__(self):
        ResetParameter.__init__(self)
        self.workflow = asb.Assembly()
        self.test_rubi = testrob.TestAssemblyRobot()
        self.test_pangpang = testrob.TestTransportRobot()
        self.init_window = Tk()

        # Specify font of labels and button's text
        global ft_label, ft_button
        ft_label = font.Font(family='Arial', size=12)
        ft_button = font.Font(size=15)

        # Specify variable for gui status
        self.gui_state = None

    def set_init_window(self):
        os.chdir(f"{PATH}\images")
        # Set the title, icon, size of the initial window
        self.init_window.title("AutoBASS GUI")
        self.init_window.iconbitmap("Robotarm.ico")
        self.init_window.geometry("820x450")

        for widget in self.init_window.winfo_children():
            widget.destroy()

        init_frame = LabelFrame(self.init_window, padx=50, pady=20, borderwidth=5)
        init_frame.grid(row=0, column=0, padx=20, pady=25)

        init_label_1 = Label(init_frame, text="Select from following operations:", pady=5, font=('Arial', 14))
        init_label_1.grid(row=0, column=0, columnspan=3, pady=30)

        init_btn_1 = Button(init_frame, text="Assembly Coin Cell", font=ft_button,\
                    padx=10, pady=40, border=5, borderwidth=4, command=self.set_assembly_window)
        init_btn_2 = Button(init_frame, text="Calibrate Robots", font=ft_button,\
                    padx=20, pady=38, border=5, borderwidth=4, command=self.set_calibration_window)
        init_btn_3 = Button(init_frame, text="Shut Down System", font=ft_button,\
                        padx=10, pady=38, border=5, borderwidth=4, command=self.shutdown_system)
        exit_btn = Button(self.init_window, text="Exit", font=ft_button,\
                    padx=52, borderwidth=4, command=self.init_window.destroy)

        init_btn_1.grid(row=1, column=0, padx=10)
        init_btn_2.grid(row=1, column=1, padx=10)
        init_btn_3.grid(row=1, column=2, padx=10)
        exit_btn.grid(row=2, column=0)

        self.init_window.mainloop()

    def set_assembly_window(self):
        
        self.init_window.title("Cell Assembly Interface")
        self.init_window.geometry("425x600")

        for widget in self.init_window.winfo_children():
            widget.destroy()

        # Create status bar
        self.assembly_status = StringVar()
        status_label = Label(self.init_window, textvariable=self.assembly_status, font=('Arial', 13), height=2, bd=2, relief=SUNKEN)
        status_label.grid(row=0, column=0, sticky=W+E)
        self.assembly_status.set("Initiate System and Give the Start and End number")

        # Creat input frame
        assembly_frame = LabelFrame(self.init_window, padx=20, pady=10)
        assembly_frame.grid(row=1, column=0, padx=20, pady=10)

        # Creat input frame
        input_frame = LabelFrame(assembly_frame, padx=50, pady=20)
        input_frame.grid(row=0, column=0, columnspan=2, pady=10)

        # Creat labels
        start_number_label = Label(input_frame, text="First Cell to assemble:", pady=15, font=ft_label)
        end_number_label = Label(input_frame, text="Last Cell to assemble:", pady=15, font=ft_label)

        start_number_label.grid(row=0, column=0)
        end_number_label.grid(row=1, column=0)
        
        # Create input fields
        global start_number_input, end_number_input
        start_number_input = Entry(input_frame, width=10, borderwidth=5)
        end_number_input = Entry(input_frame, width=10, borderwidth=5)

        start_number_input.grid(row=0, column=1)
        end_number_input.grid(row=1, column=1)

        # Create assembly button
        global assembly_btn, initiate_btn, config_btn, abort_btn, prime_pump_btn
        config_btn = Button(assembly_frame, text="Config System",  padx=3, pady=24, borderwidth=4, font=ft_button, command=self.start_config_gui)
        initiate_btn = Button(assembly_frame, text="Initiate System", padx=3, borderwidth=4, font=ft_button, command=self.init_assembly_system)
        prime_pump_btn = Button(assembly_frame, text="Prime Pump", padx=15, borderwidth=4, font=ft_button, command=self.workflow.dispensor.prime_pump)
        assembly_btn = Button(assembly_frame, text="Start Assembly", padx=85, pady=25, borderwidth=4, font=ft_button, command=self.verify_assembly_input)
        back_btn = Button(self.init_window, text="Back", borderwidth=4, padx=34, font=ft_button, command=self.set_init_window)
        exit_btn = Button(self.init_window, text="Exit", borderwidth=4, padx=40, font=ft_button, command=self.init_window.destroy)
        
        config_btn.grid(row=2, column=0, rowspan=2, padx=5)
        initiate_btn.grid(row=2, column=1, padx=5)
        prime_pump_btn.grid(row=3, column=1, padx=5)
        assembly_btn.grid(row=4, column=0, columnspan=2, pady=10)
        back_btn.grid(row=3, column=0, pady=5)
        exit_btn.grid(row=4, column=0, pady=5)

        if self.workflow._sys_is_on != True:
            start_number_input['state'] = 'disabled'
            end_number_input['state'] = 'disabled'
            assembly_btn['state'] = 'disabled'
            prime_pump_btn['state'] = 'disabled'

    def set_calibration_window(self):
        # Start a new window
        #self.init_window = Toplevel()
        self.init_window.title("Robot Calibration Interface")
        #self.init_window.iconbitmap("Robotarm.ico")
        self.init_window.geometry("570x450")

        for widget in self.init_window.winfo_children():
            widget.destroy()

        # Creat input frame
        cali_frame = LabelFrame(self.init_window, padx=50, pady=50, bd=5)
        cali_frame.grid(row=0, column=0, padx=20, pady=25)

        # Creat labels
        cali_label_1 = Label(cali_frame, text="Select The Robot to test:", pady=5, font=ft_label)
        cali_label_1.grid(row=0, column=0, columnspan=3, pady=10)

        # Create choices of testing robots
        cali_btn_1 = Button(cali_frame, text="Assembly Robot", font=ft_button,\
                        padx=10, pady=40, border=5, borderwidth=4, command=self.test_assembly)
        cali_btn_2 = Button(cali_frame, text="Transport Robot", font=ft_button, padx=15,\
                        pady=40, border=5, borderwidth=4, command=self.test_transport)
        exit_btn = Button(self.init_window, text="Exit", font=ft_button,\
                    padx=40, borderwidth=4, command=self.init_window.destroy)
        back_btn = Button(self.init_window, text="Back", font=ft_button, padx=34,\
                borderwidth=4, command=self.set_init_window)

        cali_btn_1.grid(row=1, column=0, padx=10)
        cali_btn_2.grid(row=1, column=1, padx=10)
        back_btn.grid(row=2, column=0, pady=5)
        exit_btn.grid(row=3, column=0, padx=10, pady=5)
        
    def test_assembly(self):
        self.gui_state = 'TestAssembly'
        self.init_window.state(newstate='iconic')
        self.test_rubi.set_test_assembly()

    def test_transport(self):
        self.gui_state = 'TestTransport'
        self.init_window.state(newstate='iconic')
        self.test_pangpang.init_trans_test_gui()

    def verify_assembly_input(self):
        try:
            self.start_number = int(start_number_input.get())
            self.end_number = int(end_number_input.get())
        except ValueError:
            messagebox.showerror("Input Error!", "Please put in Numbers!")
            start_number_input.delete(0, END)
            end_number_input.delete(0, END)
            self.assembly_status.set("Please put in numbers")
        else:
            if self.start_number <= 0 or self.start_number > 64 or self.end_number <= 0 or self.end_number > 64:
                messagebox.showerror("Input Error", "Input Numbers are out of range (1-64)!")
                start_number_input.delete(0, END)
                end_number_input.delete(0, END)
                self.assembly_status.set("Input Numbers are out of range!")
            elif self.end_number < self.start_number:
                messagebox.showerror("Input Error", "Starting number must be higher than ending number!")
                start_number_input.delete(0, END)
                end_number_input.delete(0, END)
                self.assembly_status.set("Starting number must be higher than ending number!")
            elif self.workflow._sys_is_on is True:
                assembly_btn["state"] = 'disabled'
                #self.assembly_rob_thread(self.start_assembly_rob)
                self.assembly_gui()
            else:
                messagebox.showerror("Error!", "System needs to be initiated first!")
    
    def assembly_gui(self):
        start_number_input['state'] = 'disabled'
        end_number_input['state'] = 'disabled'
        self.init_window.state(newstate='iconic')
        
        global asebl_prog_window, prog_text
        asebl_prog_window = Toplevel()
        asebl_prog_window.title("Assembly Progress")
        asebl_prog_window.geometry('320x220')
        prog_text = StringVar()
        prog_label = Label(asebl_prog_window, textvariable=prog_text, font=ft_label)
        progbar = ttk.Progressbar(asebl_prog_window, length=200, mode='determinate', orient=HORIZONTAL)

        global abort_btn, pause_btn
        abort_btn = Button(asebl_prog_window, text="Abort", padx=35, pady=25, borderwidth=4, font=ft_button, command=self.abort)
        pause_btn = Button(asebl_prog_window, text="Pause", padx=32, pady=25, borderwidth=4, font=ft_button, command=self.pause)
        
        progbar.grid(row=1, column=0, columnspan=2, pady=10)
        prog_label.grid(row=2, column=0, columnspan=2, pady=10)
        pause_btn.grid(row=3, column=0, padx=5, pady=10)
        abort_btn.grid(row=3, column=1, padx=5, pady=10)

        global cell_nr
        cell_nr = None
        self.workflow._stop.clear()
        self.asbl_thread = threading.Thread(target=self.start_assembly_rob)
        self.asbl_thread.setDaemon(True)
        self.asbl_thread.start()
        time.sleep(0.1)
        while self.asbl_thread.is_alive():
            progbar['value'] = self.workflow._progress['status']
            if not self.workflow._pause.is_set():
                prog_text.set(f"Assembly Paused! Cell: {cell_nr} ({self.workflow._progress['status']}%)")
            if self.workflow._stop.isSet():
                prog_text.set(f"Aborting Cell {cell_nr}...")
                asebl_prog_window.update()
                start_number_input['state'] = 'normal'
                end_number_input['state'] = 'normal'
                assembly_btn['state'] = 'normal'
                time.sleep(3)
                asebl_prog_window.destroy()
                self.init_window.state(newstate='normal')
                break
            if self.workflow._pause.is_set() and not self.workflow._stop.isSet():
                prog_text.set(f"Assembly Cell {cell_nr} in progress: ({self.workflow._progress['status']}%)")
            asebl_prog_window.update()
        else:
            progbar['value'] = 100
            prog_text.set(f"Cell {cell_nr} completed: 100%)")
            self.assembly_status.set(f"Assembly {cell_nr} completed!")
            asebl_prog_window.update()
            time.sleep(2)
            asebl_prog_window.destroy()
            start_number_input['state'] = 'normal'
            end_number_input['state'] = 'normal'
            assembly_btn['state'] = 'normal'
            self.init_window.state(newstate='normal')
    
    def init_assembly_system(self):
        self.gui_state = 'Assembly'
        os.chdir(f"{PATH}\images")
        if self.workflow._sys_is_on != True:
            initiate_btn['state'] = 'disabled'
            prog_window = Toplevel()
            prog_window.title("Assembly Robot initializing")
            prog_window.iconbitmap("Robotarm.ico")
            prog_window.geometry('280x150')
            prog_text = StringVar()
            prog_label = Label(prog_window, textvariable=prog_text, font=ft_label, pady=10, anchor=CENTER)
            prog = ttk.Progressbar(prog_window, length=250, mode='determinate', orient=HORIZONTAL)
            prog_label.grid(row=2, column=0, columnspan=2)
            prog.grid(row=1, column=0)
            count = 0
            init_thread = threading.Thread(target=self.workflow.initiate_all)
            init_thread.setDaemon(True)
            init_thread.start()
            prog.start(500)
            while True:
                prog['value'] = self.workflow._progress['status']
                prog_text.set(f"Initiating System, Please Wait ({prog['value']}%)")
                prog_window.update()
                if not init_thread.is_alive():
                    prog.stop()
                    prog['value'] = 100
                    prog_text.set(f"Initiating Complete Finishing.......({prog['value']}%)")
                    prog_window.update()
                    time.sleep(2)
                    prog_window.destroy()
                    start_number_input['state'] = 'normal'
                    end_number_input['state'] = 'normal'
                    initiate_btn['state'] = 'normal'
                    assembly_btn['state'] = 'normal'
                    prime_pump_btn['state'] = 'normal'
                    self.assembly_status.set("Initiatiing completed, click [Start Assembly] to start")
                    break
                if count >= 100:
                    raise TimeoutError
                time.sleep(1)
                count += 1
            prog_window.mainloop()
        else:
            messagebox.showinfo("Attention!", "System is already initialized!")

    def start_assembly_rob(self):
        global cell_nr
        self.workflow.apply_set_up()
        for cell_nr in range(self.start_number, self.end_number+1):
            self.assembly_status.set(f"Assembly Cell {cell_nr}")
            self.workflow.one_cell(cell_nr)
            if self.workflow._stop.isSet():
                break
            time.sleep(2)

    def check_assembly_exe(self):
        if not self.assembly_rob_exe.is_alive():
            self.assembly_status.set(f"Cell {cell_nr} Complete: 100%")
        else:
            self.assembly_status.set(f"Assembly Cell {cell_nr}: {self.workflow._progress['status']}%")
            self.init_window.after(100, self.check_assembly_exe)

    def assembly_rob_thread(self, func):
        self.assembly_rob_exe = threading.Thread(target=func)
        self.assembly_rob_exe.setDaemon(True)
        self.assembly_rob_exe.start()
        self.check_assembly_exe()

    def pause(self):
        self.workflow.pause()
        pause_btn.config(text='Resume', padx=35, command=self.resume)

    def resume(self):
        self.workflow.resume()
        pause_btn.config(text='Pause', padx=42, command=self.pause)

    def abort(self):
        self.workflow.abort()

    def shutdown_system(self):
        shutdown_thread = threading.Thread(target=self.shutdown_system_rob)
        shutdown_thread.setDaemon(True)
        shutdown_thread.start()
            
    def shutdown_system_rob(self):
        if self.gui_state == 'Assembly':
            #self.workflow.power_off()
            try:
                self.workflow.power_off()
            except:
                print("Assembly Procedure is not online!")
            else:
                messagebox.showinfo("Information", "AuoBASS is offline!")
        elif self.gui_state == 'TestAssembly':
            try:
                self.test_rubi.end_assembly_test()
            except:
                print("Assembly Test is not online!")
            else:
                messagebox.showinfo("Information", "Assembly Robot is offline!")
        elif self.gui_state == 'TestTransport':
            try:
                self.test_pangpang.end_trans_test()
            except:
                print("Transport Test is not online!")
            else:
                messagebox.showinfo("Information", "Transport Robot is offline!")
        else:
            pass

if __name__ == "__main__":
    os.chdir(PATH)
    ao = AutobassGUI()
    ao.set_init_window()