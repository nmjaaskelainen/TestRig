#calibrate the microhphone dbfs to db
#frequency magnitude to db
#window freq plot more (only include actual test)
#consider 2 freq plots, only peak and peak plus plateau after

#beautify the plots, bigger text, bigger axis, more readable

#using scipy, get fourier and db plot
from scipy.io import wavfile
from scipy.fft import rfft, rfftfreq
import glob
import os
import readline
from PyQt6 import QtWidgets
import pyqtgraph as pg
import numpy as np
import numpy.typing as npt
import math

path = "Tests"
os.chdir(path)

def complete_filename(text, state):
    return (glob.glob(text+'*.wav')+[None])[state]

class wavWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.dbPen   = pg.mkPen(color=(200, 0, 0), width=2)
        self.rmsPen  = pg.mkPen(color=(0, 0, 0), width=3)
        self.freqPen = pg.mkPen(color=(0, 0, 255), width=2)

        label_style = {"color": "black", "font-size": "12pt"}

        dbArray, dbRMS, freqArray = self.wavDecode()

        self.setWindowTitle("dBFS versus Time") #self window is dBFS

        self.dbPlot = pg.PlotWidget()
        self.setCentralWidget(self.dbPlot)
        self.dbPlot.setBackground("w")
        self.dbPlot.addLegend(labelTextColor='k')

        self.dbPlot.plot(dbArray, pen=self.dbPen, name="dBFS")
        self.dbPlot.plot(dbRMS, pen=self.rmsPen, name="Rolling Avg")
        self.dbPlot.setTitle("dBFS versus Time", color="k")
        self.dbPlot.setLabel("bottom", "Time (s)", **label_style)
        self.dbPlot.setLabel("left", "dBFS", **label_style)
        self.dbPlot.getAxis("bottom").setTextPen("k")
        self.dbPlot.getAxis("bottom").setPen("k")
        self.dbPlot.getAxis("left").setTextPen("k")
        self.dbPlot.getAxis("left").setPen("k")

        self.dbPlot.setLimits(yMin=-100, yMax=0)
        self.dbPlot.setYRange(-100, 0, padding=0)

        #make second freqWindow
        self.freqWindow = QtWidgets.QWidget()
        self.freqWindow.setWindowTitle("Frequency versus Magnitude")
        self.freqLayout = QtWidgets.QVBoxLayout(self.freqWindow)

        self.freqPlot = pg.PlotWidget()
        self.freqPlot.setBackground("w")
        self.freqPlot.plot(freqArray, pen=self.freqPen)

        self.freqPlot.setTitle("Frequency versus Magnitude", color="k")
        self.freqPlot.setLabel("bottom", "Frequency (Hz)", **label_style)
        self.freqPlot.setLabel("left", "Magnitude", **label_style)
        self.freqPlot.getAxis("bottom").setTextPen("k")
        self.freqPlot.getAxis("bottom").setPen("k")
        self.freqPlot.getAxis("left").setTextPen("k")
        self.freqPlot.getAxis("left").setPen("k")

        xMinLog = math.log10(10)    
        xMaxLog = math.log10(30000)
        self.freqPlot.setLimits(xMin=xMinLog,   xMax=xMaxLog,   
                                yMin=0,         yMax=5E10)
        self.freqPlot.setLogMode(x=True, y=False)
        self.freqPlot.setXRange(xMinLog, xMaxLog, padding=0)
        self.freqPlot.setYRange(0, 10E10, padding=0)
        self.freqLayout.addWidget(self.freqPlot)

        self.show()
        self.freqWindow.show()

    def wavDecode(self) -> tuple[npt.ArrayLike, npt.ArrayLike, npt.ArrayLike]:
        #tab completion
        readline.set_completer_delims(' \t\n;')
        readline.parse_and_bind("tab: complete")
        readline.set_completer(complete_filename)
        Fname = input("\n Input file name: ")

        start = input("\n Input start time: ")
        end = input("\n Input final time: ")

        samplerate, data = wavfile.read(Fname)

        print(f"Sampled at {samplerate}Hz")

        length = data.shape[0] / samplerate
        print(f"Total recording is {length:.2f}s")

        if start and end:
            start = float(start)
            end = float(end)

            startSample = int(start * samplerate)
            endSample = int(end * samplerate)

            data = data[startSample:endSample]

            print(f"Showing {end-start:.2f}s")

        else:
            start = 0 
            end = length    

        #normalize audio data
        dataNorm = data / 2147483648.0

        #avoid log 0 via epsilon
        epsilon = 1e-10
        db = 20 * np.log10(np.abs(dataNorm) + epsilon)

        dbMax = np.max(db)

        print(f"Max dBFS is {dbMax:.2f} dBFS")

        time = np.linspace(start, end, data.shape[0])

        dbArray = np.stack((time, db), axis=1)
        dbRMS = rollingAverage(dbArray)

        RMSmax = max(dbRMS[:, 1])
        print(f"Max dBFS RMS is {RMSmax:.2f} dBFS")

        fft_spectrum = rfft(data)
        magnitude = np.abs(fft_spectrum)

        frequencies = rfftfreq(len(data), d=1/samplerate)

        index = np.argmax(magnitude)
        freqMax = frequencies[index]

        print(f"Most signifigant frequency is {freqMax:.2f} Hz")

        freqArray = np.stack((frequencies, magnitude), axis=1)

        return dbArray, dbRMS, freqArray

@staticmethod
def rollingAverage(arr:npt.ArrayLike) -> npt.ArrayLike:
        sampleWindow = 0.010 #10 ms (in seconds)

        time = arr[:, 0]
        vals = arr[:, 1]

        samples = len(time)
        aTPS = (np.max(time) - np.min(time)) / samples #average time per sample
        numSPW = round(sampleWindow / aTPS) #number of samples per window

        valsSquar = vals ** 2
        kernel = np.ones(numSPW) #kernel is the filter to apply, moving average is a bunch of 1's
        sumSquar = np.convolve(valsSquar, kernel, mode="valid")  #convolving is complicated ``
        rmsVals = np.sqrt(sumSquar / numSPW)
        offset = numSPW // 2

        time = time[offset : offset + len(rmsVals)] #trim time to exclude the un-rms-able values
        return np.column_stack((time, -rmsVals))

            
app = QtWidgets.QApplication([])
main = wavWindow()
main.show()
app.exec()