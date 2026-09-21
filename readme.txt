graphing.py is for data logging. Use with the test rig board (shown in the Schematic) to log data. Connect the Arduino via USB then press the button to start logging the test. 

graphMaker.py is for graph editing and recreation. It takes a CSV file and produces a graph. It provides basic title editing, but need manual intervention for x-y max / mins or other graph features.

wav.py is for decoding lossless audio (.wav) files. It gives dBFS results and performs an FFT to determine most signifigant frequency.

results.py is for collecting the results of multiple tests. It outputs all of the information to a .JSON file that makes viewing the data easy.

main.cpp is the Arduino code for graphing.py. It should be uploaded to an Arduino nano and connected according to the schematic.
