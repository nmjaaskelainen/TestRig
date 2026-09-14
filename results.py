#get test numbers / range, output results file with T## - XX dB - XX Freq & XX Freq Intensity
import readline
import os
import json
import glob
import re

def completeJSON(text, state):
    return (glob.glob(text+'*.JSON')+[None])[state]

def completeJSON(text, state):
    return (glob.glob(text+'*.wav')+[None])[state]

path = "Tests"
os.chdir(path)

testToGraph = []

pattern = r"T\d\d"

moreTests = True
while moreTests: #get tests 
    another = ""

    testNo = input("\n Input test number (TXX) or END: ")
    if re.fullmatch(pattern, testNo):
        testToGraph.append(testNo)

    elif testNo == "END":
        moreTests = False

    else:
        print("Invalid test number!")
        continue


for testNo in testToGraph: #get test results
    testSucess = True
    minTime = 0
    maxTime = 99

    Fname = completeJSON(testNo)

    try:
        with open(Fname, 'r', encoding='utf-8') as file:
            data = json.load(file)

            if data['TestSuccess'] == False:
                print("Error: Test " + testNo + " failed.")
                continue

    except json.JSONDecodeError:
        print("Error: The file contains invalid formatting.")
        continue

    minTime = data['MinTime']
    maxTime = data['MaxTime']

    samplerate, data = wavfile.read(Fname)

    print(f"Sampled at {samplerate}Hz")

    length = data.shape[0] / samplerate
    print(f"Total recording is {length:.2f}s")

#TODO: output results

