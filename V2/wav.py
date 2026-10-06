import sys
import os
import re
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QDoubleValidator
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout,
    QHBoxLayout, QWidget, QCheckBox, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QLabel, QSlider, QLineEdit
)
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from wavTool import wavTool
import math


class wavWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.currentWav = None
        self.setWindowTitle("Wav Decoder")
        self.resize(1000, 600)

        #main window
        mainWidget = QWidget()
        self.setCentralWidget(mainWidget)
        mainLayout = QHBoxLayout(mainWidget)

        #graph window
        leftLayout = QVBoxLayout()
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        leftLayout.addWidget(self.canvas)

        sliderLayout = self.makeTimeBar()
        leftLayout.addLayout(sliderLayout)

        sideLayout = self.makeSideBar()

        mainLayout.addLayout(leftLayout, stretch=3)
        mainLayout.addLayout(sideLayout, stretch=1)

        self.loadTestFolders()

    def makeSideBar(self) -> QVBoxLayout:
        sideLayout = QVBoxLayout()

        #plot checkboxes
        self.cbShowDb = QCheckBox("Show dB / dBRMS")
        self.cbShowDb.setChecked(True)
        self.cbShowDb.stateChanged.connect(self.updatePlot)

        self.cbShowFft = QCheckBox("Show Frequency (FFT)")
        self.cbShowFft.setChecked(True)
        self.cbShowFft.stateChanged.connect(self.updatePlot)

        sideLayout.addWidget(self.cbShowDb)
        sideLayout.addWidget(self.cbShowFft)

        #wav list
        self.testListWidget = QListWidget()
        self.testListWidget.itemClicked.connect(self.onTestSelected)
        sideLayout.addWidget(self.testListWidget)

        #export button
        exportButton = QPushButton("Export Plot")
        exportButton.clicked.connect(self.exportPlot)
        sideLayout.addWidget(exportButton)

        return sideLayout

    #bottom time sliders
    def makeTimeBar(self) -> QHBoxLayout:
        sliderLayout = QHBoxLayout()

        #start time
        self.minSliderLabel = QLabel("Start Time (s):")
        self.minTimeEdit = QLineEdit("0.00")
        self.minTimeEdit.setFixedWidth(60)
        self.minTimeEdit.setValidator(QDoubleValidator(0.0, 100000.0, 2))
        
        self.minTimeSlider = QSlider(Qt.Orientation.Horizontal)
        self.minTimeSlider.setMinimum(0)
        self.minTimeSlider.setMaximum(100)

        #end time
        self.maxSliderLabel = QLabel("End Time (s):")
        self.maxTimeEdit = QLineEdit("0.00")
        self.maxTimeEdit.setFixedWidth(60)
        self.maxTimeEdit.setValidator(QDoubleValidator(0.0, 100000.0, 2))

        self.maxTimeSlider = QSlider(Qt.Orientation.Horizontal)
        self.maxTimeSlider.setMinimum(0)
        self.maxTimeSlider.setMaximum(100)

        #connections
        self.minTimeSlider.valueChanged.connect(self.onSliderChanged)
        self.maxTimeSlider.valueChanged.connect(self.onSliderChanged)
        self.minTimeEdit.editingFinished.connect(self.onTextEdited)
        self.maxTimeEdit.editingFinished.connect(self.onTextEdited)

        sliderLayout.addWidget(self.minSliderLabel)
        sliderLayout.addWidget(self.minTimeEdit)
        sliderLayout.addWidget(self.minTimeSlider)
        sliderLayout.addSpacing(15)
        sliderLayout.addWidget(self.maxSliderLabel)
        sliderLayout.addWidget(self.maxTimeEdit)
        sliderLayout.addWidget(self.maxTimeSlider)

        return sliderLayout
        
    def getTestsDirectory(self) -> str:
        v2Dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(v2Dir, "..", "Tests"))

    #load all test data
    def loadTestFolders(self):
        self.testListWidget.clear()
        testsDir = self.getTestsDirectory()

        if not os.path.exists(testsDir):
            return

        folders = []
        for entry in os.listdir(testsDir):
            fullPath = os.path.join(testsDir, entry)

            if os.path.isdir(fullPath):
                match = re.match(r"^T(\d+)$", entry)

                if match:
                    testNum = int(match.group(1))

                    if testNum >= 7: #only include T07+
                        folders.append((testNum, entry, fullPath))

        folders.sort(key=lambda x: x[0])

        for _, folderName, fullPath in folders:
            item = QListWidgetItem(folderName)
            item.setForeground(QColor("#000000"))

            #set test color
            try:
                wav = wavTool(fullPath)
                if not wav.dataLoaded: #no wav
                    item.setBackground(QColor("#FFB347"))

                elif wav.testSuccess: #success
                    item.setBackground(QColor("#A8E6CF"))

                else: #failure
                    item.setBackground(QColor("#FF8B94"))

            except Exception:
                item.setBackground(QColor("#FFB347"))

            self.testListWidget.addItem(item)

    #when you pick a test
    def onTestSelected(self, item):
        folderName = item.text()
        testsDir = self.getTestsDirectory()
        fullPath = os.path.join(testsDir, folderName)

        try:
            self.currentWav = wavTool(fullPath)
            if not self.currentWav.dataLoaded:
                raise ValueError("WAV file was not found or is corrupted.")

            totalDur = self.currentWav.totalDuration
            sliderMax = max(1, int(totalDur * 100))

            self.minTimeSlider.blockSignals(True)
            self.maxTimeSlider.blockSignals(True)

            self.minTimeSlider.setMaximum(sliderMax)
            self.maxTimeSlider.setMaximum(sliderMax)

            minVal = int(self.currentWav.minTime * 100)
            maxVal = int(self.currentWav.maxTime * 100)

            self.minTimeSlider.setValue(minVal)
            self.maxTimeSlider.setValue(maxVal)

            self.minTimeSlider.blockSignals(False)
            self.maxTimeSlider.blockSignals(False)

            self.syncEditFieldsFromSliders()
            self.updatePlot()

        except Exception as e:
            self.currentWav = None
            self.updatePlot()
            msg = QMessageBox(self)
            msg.setWindowTitle("WAV Loading Error")
            msg.setText(f"Could not load test '{folderName}': {str(e)}")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()

    #if time slider is adjusted
    def onSliderChanged(self):
        if self.minTimeSlider.value() > self.maxTimeSlider.value():
            if self.sender() == self.minTimeSlider:
                self.maxTimeSlider.setValue(self.minTimeSlider.value())

            else:
                self.minTimeSlider.setValue(self.maxTimeSlider.value())

        self.syncEditFieldsFromSliders()
        self.updatePlot()

    #if time input is changed
    def onTextEdited(self):
        try:
            minSec = float(self.minTimeEdit.text())

        except ValueError:
            minSec = self.minTimeSlider.value() / 100.0

        try:
            maxSec = float(self.maxTimeEdit.text())

        except ValueError:
            maxSec = self.maxTimeSlider.value() / 100.0

        maxLimit = self.maxTimeSlider.maximum() / 100.0
        minSec = max(0.0, min(minSec, maxLimit))
        maxSec = max(0.0, min(maxSec, maxLimit))

        if minSec > maxSec:
            if self.sender() == self.minTimeEdit:
                maxSec = minSec
            else:
                minSec = maxSec

        self.minTimeSlider.blockSignals(True)
        self.maxTimeSlider.blockSignals(True)
        self.minTimeSlider.setValue(int(round(minSec * 100)))
        self.maxTimeSlider.setValue(int(round(maxSec * 100)))
        self.minTimeSlider.blockSignals(False)
        self.maxTimeSlider.blockSignals(False)

        self.syncEditFieldsFromSliders()
        self.updatePlot()

    def syncEditFieldsFromSliders(self):
        minSec = self.minTimeSlider.value() / 100.0
        maxSec = self.maxTimeSlider.value() / 100.0

        self.minTimeEdit.blockSignals(True)
        self.maxTimeEdit.blockSignals(True)
        self.minTimeEdit.setText(f"{minSec:.2f}")
        self.maxTimeEdit.setText(f"{maxSec:.2f}")
        self.minTimeEdit.blockSignals(False)
        self.maxTimeEdit.blockSignals(False)

    #plot test data
    def updatePlot(self):
        self.figure.clear()
        if self.currentWav is None or not self.currentWav.dataLoaded:
            self.canvas.draw()
            return

        showDb = self.cbShowDb.isChecked()
        showFft = self.cbShowFft.isChecked()

        if not showDb and not showFft:
            self.canvas.draw()
            return

        minTime = self.minTimeSlider.value() / 100.0
        maxTime = self.maxTimeSlider.value() / 100.0

        plotCount = (1 if showDb else 0) + (1 if showFft else 0)
        currentPlotIdx = 1

        if showDb:
            axDb = self.figure.add_subplot(plotCount, 1, currentPlotIdx)
            currentPlotIdx += 1

            dbData = self.currentWav.dbData
            dbRmsData = self.currentWav.dbRmsData

            if len(dbData) > 0:
                maskDb = (dbData[:, 0] >= minTime) & (dbData[:, 0] <= maxTime)
                axDb.plot(dbData[maskDb, 0], dbData[maskDb, 1], label="dB", color="#B0C4DE", alpha=0.7, linewidth=1)

            if len(dbRmsData) > 0:
                maskRms = (dbRmsData[:, 0] >= minTime) & (dbRmsData[:, 0] <= maxTime)
                axDb.plot(dbRmsData[maskRms, 0], dbRmsData[maskRms, 1], label="dBRMS", color="#D9534F", linewidth=1.5)

            axDb.set_title("Sound Level (dB / dBRMS)")
            axDb.set_xlabel("Time (s)")
            axDb.set_ylabel("Level (dB)")
            axDb.set_ylim(-100, 0)
            axDb.legend(loc="upper right")
            axDb.grid(True)

        if showFft:
            axFft = self.figure.add_subplot(plotCount, 1, currentPlotIdx)

            sampleRate = self.currentWav.sampleRate
            data = self.currentWav.data
            timeArray = self.currentWav.timeArray

            if len(data) > 0 and sampleRate > 0:
                maskSignal = (timeArray >= minTime) & (timeArray <= maxTime)
                slicedData = data[maskSignal]

                if len(slicedData) > 0:
                    freqs, dbFS = self.currentWav.fft(slicedData)
                    axFft.plot(freqs, dbFS, color="#2E8B57", linewidth=1)

            axFft.set_title("Frequency Spectrum")
            axFft.set_xlabel("Frequency (Hz)")
            axFft.set_ylabel("Magnitude (dBFS)")
            axFft.set_xscale("log")
            axFft.set_xlim(10, 30000)
            axFft.set_ylim(-120, 0)
            axFft.grid(True, which="both")

        self.figure.tight_layout()
        self.canvas.draw()

    def exportPlot(self):
        if self.currentWav is None or not self.currentWav.dataLoaded:
            return
        filePath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Plot",
            f"{self.currentWav.testName}_plot.png",
            "PNG Image (*.png);;PDF File (*.pdf);;SVG Vector (*.svg)"
        )
        if filePath:
            self.figure.savefig(filePath)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = wavWindow()
    win.show()
    sys.exit(app.exec())