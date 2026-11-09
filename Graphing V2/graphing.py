import sys
import os
import csv
from datetime import datetime

import serial
import serial.tools.list_ports

import pyqtgraph as pg

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QLineEdit, QSlider, QFileDialog,
    QMessageBox, QStackedWidget, QListWidget, QListWidgetItem
)

def getTestsDirectory() -> str:
    v2Dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(v2Dir, "..", "Tests"))

DEFAULT_BAUDRATE = 115200
DEFAULT_PORT = "COM3"
DEFAULT_TESTS_DIR = getTestsDirectory()
MAX_REALTIME_POINTS = 500
UPDATE_INTERVAL_MS = 50

class SerialReaderThread(QThread):
    testStarted = pyqtSignal()
    testStopped = pyqtSignal(str, list, list)
    dataReceived = pyqtSignal(float, float)
    connectionError = pyqtSignal(str)

    def __init__(self, portName, baudRate):
        super().__init__()
        self.portName = portName
        self.baudRate = baudRate
        self.isExecuting = True
        self.ser = None

    def stop(self):
        self.isExecuting = False
        if self.ser and self.ser.is_open:
            self.ser.close()

    def run(self):
        try:
            self.ser = serial.Serial(self.portName, self.baudRate, timeout=0.1)
        except Exception as e:
            self.connectionError.emit(str(e))
            return

        onTest = False
        fileName = ""
        timeBuffer = []
        pressureBuffer = []

        while self.isExecuting and self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                if line == "TESTON":
                    onTest = True
                    fileName = datetime.now().strftime("%Y-%m-%d-%H_%M_%S")
                    timeBuffer.clear()
                    pressureBuffer.clear()
                    self.testStarted.emit()
                    continue

                if line == "TESTOFF":
                    if onTest:
                        onTest = False
                        self.saveData(fileName, timeBuffer, pressureBuffer)
                        self.testStopped.emit(fileName, list(timeBuffer), list(pressureBuffer))
                    continue

                if onTest:
                    parts = line.split(",")
                    if len(parts) >= 2:
                        try:
                            tVal = float(parts[0])
                            pVal = float(parts[1])
                            timeBuffer.append(tVal)
                            pressureBuffer.append(pVal)
                            self.dataReceived.emit(tVal, pVal)
                        except ValueError:
                            pass
            except Exception as e:
                if self.isExecuting:
                    self.connectionError.emit(str(e))
                break

        if self.ser and self.ser.is_open:
            self.ser.close()

    def saveData(self, fileName, timeList, pressureList):
        testsDir = DEFAULT_TESTS_DIR
        if not os.path.exists(testsDir):
            os.makedirs(testsDir)
        filePath = os.path.join(testsDir, f"{fileName}.csv")
        try:
            with open(filePath, "w", encoding="utf-8") as f:
                f.write(f"TIME:, {fileName}\n")
                f.write("Time (ms), Pressure (psi)\n")
                for t, p in zip(timeList, pressureList):
                    f.write(f"{t},{p}\n")
        except Exception as e:
            print(f"Error saving file: {e}")


class GraphingWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serialThread = None
        self.testsDir = DEFAULT_TESTS_DIR
        self.loadedTimeData = []
        self.loadedPressureData = []
        self.loadedFileName = ""

        self.liveTimeData = []
        self.livePressureData = []

        self.setupUi()
        self.refreshComPorts()
        self.loadSavedFileList()

        self.timer = QTimer()
        self.timer.setInterval(UPDATE_INTERVAL_MS)
        self.timer.timeout.connect(self.updateLivePlot)

    def setupUi(self):
        self.setWindowTitle("Graphing Tool")
        self.resize(1100, 650)

        mainWidget = QWidget()
        self.setCentralWidget(mainWidget)
        mainLayout = QHBoxLayout(mainWidget)

        leftLayout = QVBoxLayout()
        leftLayout.addLayout(self.makeTopControlBar())

        self.stackedWidget = QStackedWidget()
        self.viewerWidget = self.makeViewerWidget()
        self.liveWidget = self.makeLiveWidget()

        self.stackedWidget.addWidget(self.viewerWidget)
        self.stackedWidget.addWidget(self.liveWidget)
        leftLayout.addWidget(self.stackedWidget)

        sideLayout = self.makeSideBar()

        mainLayout.addLayout(leftLayout, stretch=3)
        mainLayout.addLayout(sideLayout, stretch=1)

    def makeTopControlBar(self) -> QHBoxLayout:
        bar = QHBoxLayout()

        lblPort = QLabel("COM Port:")
        self.cbPort = QComboBox()
        self.cbPort.setMinimumWidth(90)

        btnRefresh = QPushButton("Refresh")
        btnRefresh.clicked.connect(self.refreshComPorts)

        lblBaud = QLabel("Baud Rate:")
        self.cbBaud = QComboBox()
        self.cbBaud.addItems(["9600", "19200", "38400", "57600", "115200", "230400"])
        self.cbBaud.setCurrentText(str(DEFAULT_BAUDRATE))
        self.cbBaud.setEditable(True)

        self.btnConnect = QPushButton("Start Listening")
        self.btnConnect.clicked.connect(self.toggleConnection)

        bar.addWidget(lblPort)
        bar.addWidget(self.cbPort)
        bar.addWidget(btnRefresh)
        bar.addSpacing(10)
        bar.addWidget(lblBaud)
        bar.addWidget(self.cbBaud)
        bar.addSpacing(10)
        bar.addWidget(self.btnConnect)
        bar.addStretch()

        return bar

    def makeViewerWidget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        sliderLayout = QHBoxLayout()
        self.lblMinTime = QLabel("Start Time (ms):")
        self.minTimeEdit = QLineEdit("0.0")
        self.minTimeEdit.setFixedWidth(70)
        self.minTimeEdit.setValidator(QDoubleValidator(0.0, 1e8, 2))
        self.minTimeSlider = QSlider(Qt.Orientation.Horizontal)

        self.lblMaxTime = QLabel("End Time (ms):")
        self.maxTimeEdit = QLineEdit("0.0")
        self.maxTimeEdit.setFixedWidth(70)
        self.maxTimeEdit.setValidator(QDoubleValidator(0.0, 1e8, 2))
        self.maxTimeSlider = QSlider(Qt.Orientation.Horizontal)

        self.minTimeSlider.valueChanged.connect(self.onSliderChanged)
        self.maxTimeSlider.valueChanged.connect(self.onSliderChanged)
        self.minTimeEdit.editingFinished.connect(self.onTextEdited)
        self.maxTimeEdit.editingFinished.connect(self.onTextEdited)

        sliderLayout.addWidget(self.lblMinTime)
        sliderLayout.addWidget(self.minTimeEdit)
        sliderLayout.addWidget(self.minTimeSlider)
        sliderLayout.addSpacing(15)
        sliderLayout.addWidget(self.lblMaxTime)
        sliderLayout.addWidget(self.maxTimeEdit)
        sliderLayout.addWidget(self.maxTimeSlider)

        layout.addLayout(sliderLayout)

        # PyQtGraph PlotWidget for offline data viewing (Y-axis locked to 0-600 psi)
        self.viewPlot = pg.PlotWidget()
        self.viewPlot.setLabel("left", "Pressure", units="psi")
        self.viewPlot.setLabel("bottom", "Time", units="ms")
        self.viewPlot.setYRange(0, 600, padding=0)
        self.viewPlot.setLimits(yMin=0, yMax=600)

        view_box = self.viewPlot.getViewBox()
        view_box.setMouseEnabled(x=False, y=False)

        self.viewPlot.showGrid(x=True, y=True)
        self.viewCurve = self.viewPlot.plot(pen=pg.mkPen(color="#1F77B4", width=1.5))
        layout.addWidget(self.viewPlot)

        return widget

    def makeLiveWidget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        lblStatus = QLabel("--- LIVE TEST IN PROGRESS ---")
        lblStatus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lblStatus.setStyleSheet("font-weight: bold; color: #D9534F; font-size: 14px;")
        layout.addWidget(lblStatus)

        # PyQtGraph PlotWidget for real-time live data plotting (Y-axis locked to 0-600 psi)
        self.livePlot = pg.PlotWidget()
        self.livePlot.setTitle("Live Test Data")
        self.livePlot.setLabel("left", "Pressure", units="psi")
        self.livePlot.setLabel("bottom", "Time", units="ms")
        self.livePlot.setYRange(0, 600, padding=0)
        self.livePlot.setLimits(yMin=0, yMax=600)
        self.livePlot.showGrid(x=True, y=True)
        self.liveCurve = self.livePlot.plot(pen=pg.mkPen(color="#2E8B57", width=1.5))
        layout.addWidget(self.livePlot)

        return widget

    def makeSideBar(self) -> QVBoxLayout:
        sideLayout = QVBoxLayout()

        btnOpen = QPushButton("Open File...")
        btnOpen.clicked.connect(self.openFileDialog)
        sideLayout.addWidget(btnOpen)

        btnSelectFolder = QPushButton("Select Folder")
        btnSelectFolder.clicked.connect(self.selectFolderDialog)
        sideLayout.addWidget(btnSelectFolder)

        lblFiles = QLabel("Saved Tests:")
        sideLayout.addWidget(lblFiles)

        self.fileListWidget = QListWidget()
        self.fileListWidget.itemClicked.connect(self.onFileSelected)
        sideLayout.addWidget(self.fileListWidget)

        btnExport = QPushButton("Export Plot Image")
        btnExport.clicked.connect(self.exportPlotImage)
        sideLayout.addWidget(btnExport)

        return sideLayout

    def refreshComPorts(self):
        self.cbPort.clear()
        ports = [port.device for port in serial.tools.list_ports.comports()]
        if ports:
            self.cbPort.addItems(ports)
            if DEFAULT_PORT in ports:
                self.cbPort.setCurrentText(DEFAULT_PORT)
        else:
            self.cbPort.addItem(DEFAULT_PORT)

    def toggleConnection(self):
        if self.serialThread and self.serialThread.isRunning():
            self.stopListening()
        else:
            self.startListening()

    def startListening(self):
        portName = self.cbPort.currentText()
        try:
            baudRate = int(self.cbBaud.currentText())
        except ValueError:
            baudRate = DEFAULT_BAUDRATE

        self.serialThread = SerialReaderThread(portName, baudRate)
        self.serialThread.testStarted.connect(self.onTestStarted)
        self.serialThread.testStopped.connect(self.onTestStopped)
        self.serialThread.dataReceived.connect(self.onDataReceived)
        self.serialThread.connectionError.connect(self.onConnectionError)

        self.serialThread.start()
        self.btnConnect.setText("Stop Listening")
        self.cbPort.setEnabled(False)
        self.cbBaud.setEnabled(False)

    def stopListening(self):
        if self.serialThread:
            self.serialThread.stop()
            self.serialThread.wait()
            self.serialThread = None

        self.btnConnect.setText("Start Listening")
        self.cbPort.setEnabled(True)
        self.cbBaud.setEnabled(True)
        self.timer.stop()

    def onTestStarted(self):
        self.liveTimeData.clear()
        self.livePressureData.clear()
        self.liveCurve.setData([], [])
        self.livePlot.setXRange(0, 100)

        self.stackedWidget.setCurrentWidget(self.liveWidget)
        self.timer.start()

    def onDataReceived(self, tVal, pVal):
        self.liveTimeData.append(tVal)
        self.livePressureData.append(pVal)

    def updateLivePlot(self):
        if not self.liveTimeData:
            return

        xData = self.liveTimeData[-MAX_REALTIME_POINTS:]
        yData = self.livePressureData[-MAX_REALTIME_POINTS:]

        self.liveCurve.setData(xData, yData)
        minX, maxX = xData[0], xData[-1]
        if minX == maxX:
            maxX = minX + 1.0

        self.livePlot.setXRange(minX, maxX, padding=0.05)

    def onTestStopped(self, fileName, timeList, pressureList):
        self.timer.stop()
        self.stackedWidget.setCurrentWidget(self.viewerWidget)
        self.loadSavedFileList()

        self.loadedTimeData = timeList
        self.loadedPressureData = pressureList
        self.loadedFileName = fileName

        self.setupPlotLimits()
        self.updateViewerPlot()

        QMessageBox.information(self, "Test Complete", f"Test data automatically saved as {fileName}.csv")

    def onConnectionError(self, errorMsg):
        self.stopListening()
        QMessageBox.warning(self, "Serial Error", f"Serial connection error: {errorMsg}")

    def selectFolderDialog(self):
        selectedDir = QFileDialog.getExistingDirectory(self, "Select Tests Folder", self.testsDir)
        if selectedDir:
            self.testsDir = selectedDir
            self.loadSavedFileList()

    def loadSavedFileList(self):
        self.fileListWidget.clear()
        if not os.path.exists(self.testsDir):
            return

        files = [f for f in os.listdir(self.testsDir) if f.lower().endswith(".csv")]
        files.sort(reverse=True)

        for fileName in files:
            item = QListWidgetItem(fileName)
            self.fileListWidget.addItem(item)

    def openFileDialog(self):
        filePath, _ = QFileDialog.getOpenFileName(
            self, "Open Data File", self.testsDir, "CSV Files (*.csv);;All Files (*)"
        )
        if filePath:
            self.loadCsvFile(filePath)

    def onFileSelected(self, item):
        fileName = item.text()
        filePath = os.path.join(self.testsDir, fileName)
        self.loadCsvFile(filePath)

    def loadCsvFile(self, filePath: str):
        try:
            times = []
            pressures = []
            with open(filePath, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headerRead = False
                for row in reader:
                    if not row:
                        continue
                    if not headerRead:
                        if "Time" in row[0] or "TIME" in row[0]:
                            headerRead = True
                        continue

                    if len(row) >= 2:
                        try:
                            tVal = float(row[0].strip())
                            pVal = float(row[1].strip())
                            times.append(tVal)
                            pressures.append(pVal)
                        except ValueError:
                            pass

            self.loadedTimeData = times
            self.loadedPressureData = pressures
            self.loadedFileName = os.path.basename(filePath)

            self.setupPlotLimits()
            self.updateViewerPlot()
            self.stackedWidget.setCurrentWidget(self.viewerWidget)
        except Exception as e:
            QMessageBox.warning(self, "File Load Error", f"Could not load CSV file: {str(e)}")

    def setupPlotLimits(self):
        if not self.loadedTimeData:
            return

        minT = min(self.loadedTimeData)
        maxT = max(self.loadedTimeData)
        if minT == maxT:
            maxT = minT + 1.0

        sliderMax = max(1, int(maxT - minT))

        self.minTimeSlider.blockSignals(True)
        self.maxTimeSlider.blockSignals(True)

        self.minTimeSlider.setMinimum(0)
        self.minTimeSlider.setMaximum(sliderMax)
        self.maxTimeSlider.setMinimum(0)
        self.maxTimeSlider.setMaximum(sliderMax)

        self.minTimeSlider.setValue(0)
        self.maxTimeSlider.setValue(sliderMax)

        self.minTimeSlider.blockSignals(False)
        self.maxTimeSlider.blockSignals(False)

        self.syncEditFieldsFromSliders()

    def onSliderChanged(self):
        if self.minTimeSlider.value() > self.maxTimeSlider.value():
            if self.sender() == self.minTimeSlider:
                self.maxTimeSlider.setValue(self.minTimeSlider.value())
            else:
                self.minTimeSlider.setValue(self.maxTimeSlider.value())

        self.syncEditFieldsFromSliders()
        self.updateViewerPlot()

    def onTextEdited(self):
        if not self.loadedTimeData:
            return

        minT = min(self.loadedTimeData)
        maxT = max(self.loadedTimeData)

        try:
            minVal = float(self.minTimeEdit.text())
        except ValueError:
            minVal = minT

        try:
            maxVal = float(self.maxTimeEdit.text())
        except ValueError:
            maxVal = maxT

        minVal = max(minT, min(minVal, maxT))
        maxVal = max(minT, min(maxVal, maxT))

        if minVal > maxVal:
            if self.sender() == self.minTimeEdit:
                maxVal = minVal
            else:
                minVal = maxVal

        rangeT = maxT - minT
        sliderMax = self.minTimeSlider.maximum()
        if rangeT > 0:
            minSliderVal = int((minVal - minT) / rangeT * sliderMax)
            maxSliderVal = int((maxVal - minT) / rangeT * sliderMax)
        else:
            minSliderVal, maxSliderVal = 0, sliderMax

        self.minTimeSlider.blockSignals(True)
        self.maxTimeSlider.blockSignals(True)
        self.minTimeSlider.setValue(minSliderVal)
        self.maxTimeSlider.setValue(maxSliderVal)
        self.minTimeSlider.blockSignals(False)
        self.maxTimeSlider.blockSignals(False)

        self.syncEditFieldsFromSliders()
        self.updateViewerPlot()

    def syncEditFieldsFromSliders(self):
        if not self.loadedTimeData:
            self.minTimeEdit.setText("0.00")
            self.maxTimeEdit.setText("0.00")
            return

        minT = min(self.loadedTimeData)
        maxT = max(self.loadedTimeData)
        rangeT = maxT - minT
        sliderMax = self.minTimeSlider.maximum()

        if sliderMax > 0 and rangeT > 0:
            currentMin = minT + (self.minTimeSlider.value() / sliderMax) * rangeT
            currentMax = minT + (self.maxTimeSlider.value() / sliderMax) * rangeT
        else:
            currentMin, currentMax = minT, maxT

        self.minTimeEdit.blockSignals(True)
        self.maxTimeEdit.blockSignals(True)
        self.minTimeEdit.setText(f"{currentMin:.2f}")
        self.maxTimeEdit.setText(f"{currentMax:.2f}")
        self.minTimeEdit.blockSignals(False)
        self.maxTimeEdit.blockSignals(False)

    def updateViewerPlot(self):
        if not self.loadedTimeData:
            self.viewCurve.setData([], [])
            return

        try:
            startT = float(self.minTimeEdit.text())
            endT = float(self.maxTimeEdit.text())
        except ValueError:
            startT = min(self.loadedTimeData)
            endT = max(self.loadedTimeData)

        filteredTime = []
        filteredPressure = []

        for t, p in zip(self.loadedTimeData, self.loadedPressureData):
            if startT <= t <= endT:
                filteredTime.append(t)
                filteredPressure.append(p)

        self.viewPlot.setTitle(f"Test Data: {self.loadedFileName}")
        self.viewCurve.setData(filteredTime, filteredPressure)
        
        # Lock x-axis between the user-adjusted start and end times (bounded from 0 to test max)
        if startT < endT:
            self.viewPlot.setXRange(startT, endT, padding=0)

    def exportPlotImage(self):
        if not self.loadedTimeData:
            QMessageBox.information(self, "Export Plot", "No plot data available to export.")
            return

        defaultName = f"{self.loadedFileName}_plot.png" if self.loadedFileName else "plot.png"
        filePath, _ = QFileDialog.getSaveFileName(
            self, "Save Plot Image", DEFAULT_TESTS_DIR, "PNG Image (*.png)"
        )
        if filePath:
            self.viewPlot.grab().save(filePath)

    def closeEvent(self, event):
        self.stopListening()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = GraphingWindow()
    win.show()
    sys.exit(app.exec())