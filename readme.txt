graphing.py is for data logging. Use with the test rig board (shown in XXX file) to log data. Connect the Arduino via USB then press the button to start logging the test. 

graphMaker.py is for graph editing and recreation. It takes a CSV file and produces a graph. It provides basic title editing, but need manual intervention for x-y max / mins or other graph features.

main.cpp is the Arduino code for graphing.py. It should be uploaded to an Arduino nano and connected according to the schematic.