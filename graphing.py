import serial
from datetime import datetime
import matplotlib.pyplot as plt

ser = serial.Serial()
ser.port = 'COM6'
ser.baudrate = 115200

ser.open()

def getFileName():
    return datetime.now().strftime("%Y-%m-%d-%H_%M_%S.csv")

onTest = False

while True:
    raw = ser.readline().decode().strip()
    print("START")

    if raw == "TESTON":
        onTest = True
        print("--- TEST ON ---")

        Fname = getFileName()

        time = []
        voltage = []

        #OnTest - speed matters
        while onTest:
            test = ser.readline().decode().strip()

            if test == "TESTOFF":
                onTest = False
                print("--- TEST OFF ---")

                break

            data = test.split(",")
            if len(data) == 2:
                time.append(data[0])
                voltage.append(data[1])

        #Post test - do whatever
        if time:
            with open(Fname, "w") as f: 
                f.write("Time (ms), Voltage (V)\n")
                for t, v in zip(time, voltage):
                    f.write(f"{t},{v}\n")
            print("--- DATA SAVED ---")

            #plot (non-blocking)
            plt.figure(1)
            plt.clf()
            plt.plot([float(t) for t in time], [float(v) for v in voltage])
            plt.title(f"Test: {Fname}")
            plt.xlabel("Time (ms)")
            plt.ylabel("Voltage (V)")
            plt.pause(0.1)
            plt.show(block=False)

            print("--- READY --- \n \n")

        else:
            print("--- ERROR ---")   
