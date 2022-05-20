import time
import os

PATH = os.path.dirname(__file__)
#os.chdir(PATH)

def count_down_print(count_msg:str, end_msg:str="", count_time:int=3):

    for i in range(count_time, -1, -1):
        print(f"\r{count_msg} ({i}s)", end='')
        time.sleep(1)

    print(f"\r{count_msg}      {' '*len(count_msg)}", end='\r')

    if end_msg != "":
        print(f"{end_msg}{'  '*len(count_msg)}")
    else:
         print(f"\r{' '*(count_time + len(count_msg))}", end='\r')

def dynam_print(count_msg:str, end_msg:str="", count_time:int=3, waiting:float=0.05):

    for j in range(count_time+1):
        print(f"\r{count_msg}{'.'*j}", end='')
        time.sleep(waiting)
    
    print(f"\r{' '*(count_time + len(count_msg))}", end='\r')
    
    if end_msg != "":
        print(f"{end_msg}{' '*len(count_msg)}")
    else:
        print(f"\r{count_msg}{' '*len(count_msg)}", end='\r')
        print(f"\r{' '*(count_time + len(count_msg))}", end='\r')

def log_print(msg, logfile:str="operating"):

    os.chdir(f"{PATH}\logs")
    filename = {'calibrate':"cali_log.txt", 'assembly':"AutoBaSS_log.txt", 'operating': "Operation_log.txt"}

    with open (filename[logfile], "r") as f:
        states = f.readlines()

    try:
        lastdate = str(states[-1][7:17])
        time.sleep(0.01)
    except ValueError:
        pass

    with open (filename[logfile], "a") as f:

        if lastdate != time.strftime("%d/%m/%Y", time.localtime()):
            print("\n-----------------------------", file=f)

        print(time.strftime(f"[Time: %d/%m/%Y, %H:%M:%S];\tEvent: {msg}", time.localtime()), file=f)
    
    print(f"\r{' '*50}", end='\r')
    print(time.strftime(f"[Time: %d/%m/%Y, %H:%M:%S];\tEvent: {msg}", time.localtime()))