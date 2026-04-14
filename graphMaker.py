import matplotlib.pyplot as plt
import glob
import readline
import os

path = "Tests"
os.chdir(path)

XMIN = 0
XMAX = 10000
YMAX = 400

def complete_filename(text, state):
    return (glob.glob(text+'*.csv')+[None])[state]

while True:
    readline.set_completer_delims(' \t\n;')
    readline.parse_and_bind("tab: complete")
    readline.set_completer(complete_filename)
    Fname = input("\n Input file name: ")

    try:
        with open(Fname) as f:

            time = []
            pressure = []

            C1 = ""
            CN = False
            while not C1.isalpha():
                C1 = input("\n Do you want to edit the title? (Y / N): ")
                
                if C1 == "Y":
                    Fname = input("\n Input new name: ")
                    CN = True

            XMIN = float(input("\n Set XMIN: "))
            XMAX = float(input("\n Set XMAX: "))

            titles = f.readline().strip().split(",")
            fig, ax1 = plt.subplots()
            
            ax1.set_ylabel("Pressure (psi)")
            ax1.set_xlabel("Time (ms)")
            ax1.set_ylim(0, YMAX)
            ax1.set_xlim(left=XMIN, right=XMAX)

            for x in f:
                data = x.split(",")

                time.append(data[0])
                pressure.append(data[1])

            fig.suptitle(Fname)
            ax1.plot([float(t) for t in time], [float(p) for p in pressure])

            if CN:
                plt.savefig(Fname + ".png")

            plt.show()

    except FileNotFoundError:
        print("File not found")

