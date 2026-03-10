import matplotlib.pyplot as plt
import glob
import readline
import os

path = "Tests"
os.chdir(path)

def complete_filename(text, state):
    return (glob.glob(text+'*.csv')+[None])[state]

while True:
    readline.set_completer_delims(' \t\n;')
    readline.parse_and_bind("tab: complete")
    readline.set_completer(complete_filename)
    Fname = input("Input file name: ")

    try:
        with open(Fname) as f:

            time = []
            pressure = []
            microphone = []

            C1 = ""
            CN = False
            while not C1.isalpha():
                C1 = input("Do you want to edit the title? (Y / N): ")
                
                if C1 == "Y":
                    Fname = input("Input new name: ")
                    CN = True

            titles = f.readline().strip().split(",")
            fig, (ax1, ax2) = plt.subplots(2)

            print(titles)
            
            ax1.set_ylabel(titles[1])
            ax1.set_ylim(0, 1000)
            ax2.set_ylabel(titles[2])
            ax2.set_ylim(0, 5)
            ax2.set_xlabel(titles[0])

            for x in f:
                data = x.split(",")

                time.append(data[0])
                pressure.append(data[1])
                microphone.append(data[2])

            fig.suptitle(Fname)
            ax1.plot([float(t) for t in time], [float(p) for p in pressure])
            ax2.plot([float(t) for t in time], [float(m) for m in microphone])
            
            fig.tight_layout(rect=[0, 0.03, 1, 0.95])

            if CN:
                plt.savefig(Fname + ".png")

            plt.show()

    except FileNotFoundError:
        print("File not found")

