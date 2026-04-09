import serial
from datetime import datetime
import matplotlib.pyplot as plt
import os

ser = serial.Serial()
ser.port = 'COM6'
ser.baudrate = 115200
ser.open()

path = "Tests"
os.chdir(path)

def getFileName():
    return datetime.now().strftime("%Y-%m-%d-%H_%M_%S")

onTest = False

while True:
    raw = ser.readline().decode().strip()
    print("START")

    if raw == "TESTON":
        onTest = True
        plt.close('all')
        print("--- TEST ON ---")

        Fname = getFileName()

        time = []
        pressure = []

        #OnTest - speed matters
        while onTest:
            test = ser.readline().decode().strip()
            
            if not test:
                continue

            if test == "TESTOFF":
                onTest = False
                print("--- TEST OFF ---")

                break

            data = test.split(",")
            if len(data) > 1:
                time.append(data[0])
                pressure.append(data[1])

        #Post test - do whatever
        if time:
            with open(Fname + ".csv", "w") as f: 
                f.write(f"TIME:, {Fname}\n")
                f.write("Time (ms), Pressure (psi)\n")
                for t, p in zip(time, pressure):
                    f.write(f"{t},{p}\n")
            print("--- DATA SAVED ---")

            #plot
            fig, ax1 = plt.subplots()
            
            fig.suptitle(f"Test: {Fname}")
            ax1.plot([float(t) for t in time], [float(p) for p in pressure])
            
            ax1.set_ylabel("Pressure (psi)")
            ax1.set_ylim(0, 1000)
            ax1.set_xlabel("Time (ms)")

            fig.tight_layout(rect=[0, 0.03, 1, 0.95])
            plt.pause(0.1)
            plt.savefig(Fname)
            plt.show()

            print("--- READY --- \n \n")

        else:
            print("--- ERROR ---")   
