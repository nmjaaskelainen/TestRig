import matplotlib.pyplot as plt
import glob
import readline
import os

path = "/Tests/"
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
            voltage = []

            C1 = ""
            CN = False
            while not C1.isalpha():
                C1 = input("Do you want to edit the title? (Y / N): ")
                
                if C1 == "Y":
                    name2 = input("Input new name: ")
                    CN = True

            Fname = name2

            titles = f.readline().split(",")

            plt.title(Fname)
            plt.xlabel(titles[0])
            plt.ylabel(titles[1])

            for x in f:
                data = x.split(",")

                time.append(data[0])
                voltage.append(data[1])

            plt.plot([float(t) for t in time], [float(v) for v in voltage])

            if CN:
                plt.savefig(name2 + ".png")

            plt.show()

    except FileNotFoundError:
        print("File not found")

