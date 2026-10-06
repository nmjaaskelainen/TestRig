import serial
from datetime import datetime
import matplotlib.pyplot as plt
import os
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import Qt

ser = serial.Serial()
ser.port = 'COM3'
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My First PyQt6 App")
        self.resize(400, 200)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.label = QLabel("Hello! Click the button below.", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.button = QPushButton("Click Me", self)
        self.button.clicked.connect(self.on_button_click)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.button)
        central_widget.setLayout(layout)

    def on_button_click(self):
        self.label.setText("Button clicked! PyQt6 is working flawlessly.")
