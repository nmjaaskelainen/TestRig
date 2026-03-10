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
        microphone = []

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
            if len(data) == 3:
                time.append(data[0])
                pressure.append(data[1])
                microphone.append(data[2])

        #Post test - do whatever
        if time:
            with open(Fname + ".csv", "w") as f: 
                f.write("Time (ms), Pressure (psi), Microphone (V)\n")
                for t, p, m in zip(time, pressure, microphone):
                    f.write(f"{t},{p},{m}\n")
            print("--- DATA SAVED ---")

            #plot
            fig, (ax1, ax2) = plt.subplots(2)
            
            fig.suptitle(f"Test: {Fname}")
            ax1.plot([float(t) for t in time], [float(p) for p in pressure])
            ax2.plot([float(t) for t in time], [float(m) for m in microphone])
            
            ax1.set_ylabel("Pressure (psi)")
            ax1.set_ylim(0, 1000)
            ax2.set_ylabel("Microphone (V)")
            ax2.set_ylim(0, 5)
            ax2.set_xlabel("Time (ms)")

            fig.tight_layout(rect=[0, 0.03, 1, 0.95])
            plt.pause(0.1)
            plt.show()
            plt.savefig(Fname)

            print("--- READY --- \n \n")

        else:
            print("--- ERROR ---")   
