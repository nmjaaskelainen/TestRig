import sys
import os
import re
import wave
import tempfile
import numpy as np
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QColor, QDoubleValidator
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout,
    QHBoxLayout, QWidget, QCheckBox, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QLabel, QSlider, QLineEdit
)
import pyqtgraph as pg
from wavTool import wavTool

class wavWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.currentWav = None
        self.currentWavPath = None
        self.tempWavPath = None
        self.currentSpeed = 1.0
        self.testsDir = self.getTestsDirectory()
        self.playheadLine = None

        self.audioOutput = QAudioOutput()
        self.mediaPlayer = QMediaPlayer()
        self.mediaPlayer.setAudioOutput(self.audioOutput)
        self.mediaPlayer.positionChanged.connect(self.onPlaybackPositionChanged)
        self.mediaPlayer.playbackStateChanged.connect(self.onPlaybackStateChanged)

        self.setWindowTitle("Wav Decoder (PyQtGraph)")
        self.resize(1100, 650)

        mainWidget = QWidget()
        self.setCentralWidget(mainWidget)
        mainLayout = QHBoxLayout(mainWidget)

        leftLayout = QVBoxLayout()
        sliderLayout = self.makeTimeBar()
        leftLayout.addLayout(sliderLayout)

        # PyQtGraph GraphicsLayoutWidget container for multiple subplots (dB and FFT)
        self.plotWidget = pg.GraphicsLayoutWidget()
        leftLayout.addWidget(self.plotWidget)

        # Setup subplots inside the graphics layout
        self.dbPlot = self.plotWidget.addPlot(row=0, col=0)
        self.dbPlot.showGrid(x=False, y=False)
        self.dbPlot.setTitle("Sound Level")
        self.dbPlot.setLabel("left", "Level", units="dB")
        self.dbPlot.setLabel("bottom", "Time", units="s")
        self.dbPlot.setYRange(40, 120)
        self.dbPlot.addLegend()

        self.dbCurve = self.dbPlot.plot(pen=pg.mkPen(color="#B0C4DE", width=1), name="dB")
        self.dbRmsCurve = self.dbPlot.plot(pen=pg.mkPen(color="#D9534F", width=1.5), name="dBRMS")
        
        # Playhead vertical line on dbPlot
        self.playheadLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(color="#E74C3C", width=1.5, style=Qt.PenStyle.DashLine))
        self.dbPlot.addItem(self.playheadLine)

        self.plotWidget.nextRow()

        self.fftPlot = self.plotWidget.addPlot(row=1, col=0)
        self.fftPlot.showGrid(x=False, y=False)
        self.fftPlot.setTitle("Frequency Spectrum")
        self.fftPlot.setLabel("left", "Magnitude", units="dB")
        self.fftPlot.setLabel("bottom", "Frequency", units="Hz")
        self.fftPlot.getAxis("bottom").enableAutoSIPrefix(False)
        self.fftPlot.setLogMode(True, False)
        self.fftPlot.setXRange(np.log10(10), np.log10(30000))

        major_ticks = [(exp, f"{10**exp}") for exp in range(0, 6)]
        self.fftPlot.getAxis("bottom").setTicks([major_ticks])

        self.fftPlot.setYRange(0, 80)
        self.fftCurve = self.fftPlot.plot(pen=pg.mkPen(color="#2E8B57", width=1))

        playbackLayout = self.makePlaybackBar()
        leftLayout.addLayout(playbackLayout)

        sideLayout = self.makeSideBar()
        mainLayout.addLayout(leftLayout, stretch=3)
        mainLayout.addLayout(sideLayout, stretch=1)
        self.loadTestFolders()
        self.selectDefaultTest()

    def makeSideBar(self) -> QVBoxLayout:
        sideLayout = QVBoxLayout()

        openFolderButton = QPushButton("Open Folder")
        openFolderButton.clicked.connect(self.selectFolder)
        sideLayout.addWidget(openFolderButton)

        self.cbShowDb = QCheckBox("Show dB / dBRMS")
        self.cbShowDb.setChecked(True)
        self.cbShowDb.stateChanged.connect(self.updatePlot)
        self.cbShowFft = QCheckBox("Show Frequency (FFT)")
        self.cbShowFft.setChecked(True)
        self.cbShowFft.stateChanged.connect(self.updatePlot)
        sideLayout.addWidget(self.cbShowDb)
        sideLayout.addWidget(self.cbShowFft)

        self.testListWidget = QListWidget()
        self.testListWidget.itemClicked.connect(self.onTestSelected)
        sideLayout.addWidget(self.testListWidget)

        exportButton = QPushButton("Export Plot")
        exportButton.clicked.connect(self.exportPlot)
        sideLayout.addWidget(exportButton)
        return sideLayout

    def makePlaybackBar(self) -> QHBoxLayout:
        playbackLayout = QHBoxLayout()
        self.playPauseButton = QPushButton("Play")
        self.playPauseButton.clicked.connect(self.togglePlayPause)

        resetBtn = QPushButton("Reset")
        resetBtn.clicked.connect(self.resetPlaybackToStart)

        timeLabel = QLabel("Current Time (s):")
        self.playbackTimeEdit = QLineEdit("0.00")
        self.playbackTimeEdit.setFixedWidth(60)
        self.playbackTimeEdit.setValidator(QDoubleValidator(0.0, 100000.0, 2))
        self.playbackTimeEdit.editingFinished.connect(self.onPlaybackTimeEdited)

        playbackLayout.addWidget(self.playPauseButton)
        playbackLayout.addWidget(resetBtn)
        playbackLayout.addWidget(timeLabel)
        playbackLayout.addWidget(self.playbackTimeEdit)
        playbackLayout.addSpacing(15)

        self.speedLabel = QLabel("Speed: 1.00x")
        self.speedLabel.setFixedWidth(85)

        speedDownBtn = QPushButton("-")
        speedDownBtn.setFixedWidth(28)
        speedDownBtn.clicked.connect(lambda: self.adjustSpeed(-0.25))

        speedUpBtn = QPushButton("+")
        speedUpBtn.setFixedWidth(28)
        speedUpBtn.clicked.connect(lambda: self.adjustSpeed(0.25))

        speed05Btn = QPushButton("0.5x")
        speed05Btn.setFixedWidth(40)
        speed05Btn.clicked.connect(lambda: self.setSpeed(0.5))

        speed10Btn = QPushButton("1.0x")
        speed10Btn.setFixedWidth(40)
        speed10Btn.clicked.connect(lambda: self.setSpeed(1.0))

        speed15Btn = QPushButton("1.5x")
        speed15Btn.setFixedWidth(40)
        speed15Btn.clicked.connect(lambda: self.setSpeed(1.5))

        speed20Btn = QPushButton("2.0x")
        speed20Btn.setFixedWidth(40)
        speed20Btn.clicked.connect(lambda: self.setSpeed(2.0))

        playbackLayout.addWidget(self.speedLabel)
        playbackLayout.addWidget(speedDownBtn)
        playbackLayout.addWidget(speedUpBtn)
        playbackLayout.addWidget(speed05Btn)
        playbackLayout.addWidget(speed10Btn)
        playbackLayout.addWidget(speed15Btn)
        playbackLayout.addWidget(speed20Btn)
        playbackLayout.addSpacing(15)

        self.volumeLabel = QLabel("Vol: 100%")
        self.volumeLabel.setFixedWidth(75)
        self.volumeSlider = QSlider(Qt.Orientation.Horizontal)
        self.volumeSlider.setMinimum(0)
        self.volumeSlider.setMaximum(200)
        self.volumeSlider.setValue(100)
        self.volumeSlider.setFixedWidth(100)
        self.volumeSlider.valueChanged.connect(self.onVolumeChanged)

        playbackLayout.addWidget(self.volumeLabel)
        playbackLayout.addWidget(self.volumeSlider)
        playbackLayout.addStretch()
        return playbackLayout

    def selectFolder(self):
        selectedDir = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            self.testsDir
        )

        if selectedDir:
            self.testsDir = selectedDir
            self.currentWav = None
            self.currentWavPath = None
            self.mediaPlayer.stop()
            self.mediaPlayer.setSource(QUrl())
            self.updatePlot()
            self.loadTestFolders()
            self.selectDefaultTest()

    def selectDefaultTest(self):
        for i in range(self.testListWidget.count()):
            item = self.testListWidget.item(i)

            if item.text() == "T07":
                self.testListWidget.setCurrentItem(item)
                self.onTestSelected(item)
                break

    def makeTimeBar(self) -> QHBoxLayout:
        sliderLayout = QHBoxLayout()

        self.minSliderLabel = QLabel("Start Time (s):")
        self.minTimeEdit = QLineEdit("0.00")
        self.minTimeEdit.setFixedWidth(60)
        self.minTimeEdit.setValidator(QDoubleValidator(0.0, 100000.0, 2))
        self.minTimeSlider = QSlider(Qt.Orientation.Horizontal)
        self.minTimeSlider.setMinimum(0)
        self.minTimeSlider.setMaximum(100)

        self.minTimeSlider.valueChanged.connect(self.onSliderChanged)
        self.minTimeEdit.editingFinished.connect(self.onTextEdited)

        self.maxSliderLabel = QLabel("End Time (s):")
        self.maxTimeEdit = QLineEdit("0.00")
        self.maxTimeEdit.setFixedWidth(60)
        self.maxTimeEdit.setValidator(QDoubleValidator(0.0, 100000.0, 2))
        self.maxTimeSlider = QSlider(Qt.Orientation.Horizontal)
        self.maxTimeSlider.setMinimum(0)
        self.maxTimeSlider.setMaximum(100)

        self.maxTimeSlider.valueChanged.connect(self.onSliderChanged)
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

    def loadTestFolders(self):
        self.testListWidget.clear()
        testsDir = self.testsDir

        if not os.path.exists(testsDir):
            return
        
        folders = []
        for entry in os.listdir(testsDir):
            fullPath = os.path.join(testsDir, entry)
            if os.path.isdir(fullPath):
                match = re.match(r"^T(\d+)$", entry)
                if match:
                    testNum = int(match.group(1))
                    if testNum >= 7:
                        folders.append((testNum, entry, fullPath))

        folders.sort(key=lambda x: x[0])
        for _, folderName, fullPath in folders:
            item = QListWidgetItem(folderName)
            item.setForeground(QColor("#000000"))
            try:
                wav = wavTool(fullPath)
                if not wav.dataLoaded:
                    item.setBackground(QColor("#FFB347"))
                elif wav.testSuccess:
                    item.setBackground(QColor("#A8E6CF"))
                else:
                    item.setBackground(QColor("#FF8B94"))

            except Exception:
                item.setBackground(QColor("#FFB347"))
            self.testListWidget.addItem(item)

    def onTestSelected(self, item):
        folderName = item.text()
        testsDir = self.testsDir
        fullPath = os.path.join(testsDir, folderName)
        try:
            self.mediaPlayer.stop()
            self.currentWav = wavTool(fullPath)
            if not self.currentWav.dataLoaded:
                raise ValueError("WAV file was not found or is corrupted.")
            
            wavFilePath = None
            if os.path.isfile(fullPath) and fullPath.lower().endswith(".wav"):
                wavFilePath = fullPath
            elif os.path.isdir(fullPath):
                for file in os.listdir(fullPath):
                    if file.lower().endswith(".wav"):
                        wavFilePath = os.path.join(fullPath, file)
                        break

            self.currentWavPath = wavFilePath
            if wavFilePath:
                self.applyVolumeAndSource(preservePosition=False)
            else:
                self.mediaPlayer.setSource(QUrl())

            self.mediaPlayer.setPlaybackRate(self.currentSpeed)

            totalDur = self.currentWav.totalDuration
            sliderMax = max(1, int(totalDur * 100))

            self.minTimeSlider.blockSignals(True)
            self.minTimeSlider.setMaximum(sliderMax)
            self.maxTimeSlider.blockSignals(True)
            self.maxTimeSlider.setMaximum(sliderMax)

            minVal = int(self.currentWav.minTime * 100)
            maxVal = int(self.currentWav.maxTime * 100)

            self.minTimeSlider.setValue(minVal)
            self.minTimeSlider.blockSignals(False)
            self.maxTimeSlider.setValue(maxVal)
            self.maxTimeSlider.blockSignals(False)

            self.resetPlaybackToStart()

            self.syncEditFieldsFromSliders()
            self.updatePlot()

        except Exception as e:
            self.currentWav = None
            self.currentWavPath = None
            self.mediaPlayer.setSource(QUrl())
            self.updatePlot()
            msg = QMessageBox(self)
            msg.setWindowTitle("WAV Loading Error")
            msg.setText(f"Could not load test '{folderName}': {str(e)}")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()

    def togglePlayPause(self):
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.mediaPlayer.pause()

        else:
            if self.mediaPlayer.duration() > 0 and self.mediaPlayer.position() >= self.mediaPlayer.duration():
                self.resetPlaybackToStart()
            self.mediaPlayer.play()

    def resetPlaybackToStart(self):
        minSec = self.minTimeSlider.value() / 100.0
        self.mediaPlayer.setPosition(int(minSec * 1000))
        self.playbackTimeEdit.blockSignals(True)
        self.playbackTimeEdit.setText(f"{minSec:.2f}")
        self.playbackTimeEdit.blockSignals(False)

        if self.playheadLine is not None:
            self.playheadLine.setValue(minSec)

    def onPlaybackTimeEdited(self):
        try:
            sec = float(self.playbackTimeEdit.text())

        except ValueError:
            sec = self.mediaPlayer.position() / 1000.0

        maxLimit = self.maxTimeSlider.maximum() / 100.0
        sec = max(0.0, min(sec, maxLimit))
        self.playbackTimeEdit.blockSignals(True)
        self.playbackTimeEdit.setText(f"{sec:.2f}")
        self.playbackTimeEdit.blockSignals(False)
        self.mediaPlayer.setPosition(int(sec * 1000))

        if self.playheadLine is not None:
            self.playheadLine.setValue(sec)

    def setSpeed(self, rate: float):
        self.currentSpeed = round(rate, 2)
        self.speedLabel.setText(f"Speed: {self.currentSpeed:.2f}x")
        self.mediaPlayer.setPlaybackRate(self.currentSpeed)

    def adjustSpeed(self, delta: float):
        newSpeed = max(0.25, min(3.00, self.currentSpeed + delta))
        self.setSpeed(newSpeed)

    def onVolumeChanged(self):
        self.applyVolumeAndSource(preservePosition=True)

    def applyVolumeAndSource(self, preservePosition: bool = True):
        if not self.currentWavPath or not os.path.exists(self.currentWavPath):
            return
        
        volValue = self.volumeSlider.value()
        self.volumeLabel.setText(f"Vol: {volValue}%")
        currentPos = self.mediaPlayer.position() if preservePosition else 0
        wasPlaying = self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState

        if volValue <= 100:
            targetPath = self.currentWavPath
            self.audioOutput.setVolume(volValue / 100.0)

        else:
            self.audioOutput.setVolume(1.0)
            gainFactor = volValue / 100.0
            targetPath = self.createAmplifiedWav(self.currentWavPath, gainFactor)
        
        currentSource = self.mediaPlayer.source().toLocalFile()
        if os.path.abspath(currentSource) != os.path.abspath(targetPath):
            self.mediaPlayer.setSource(QUrl.fromLocalFile(targetPath))
            if preservePosition:
                self.mediaPlayer.setPosition(currentPos)
            if wasPlaying:
                self.mediaPlayer.play()

    def createAmplifiedWav(self, originalPath: str, gainFactor: float) -> str:
        if self.tempWavPath and os.path.exists(self.tempWavPath):
            try:
                os.remove(self.tempWavPath)
            except Exception:
                pass

        try:
            with wave.open(originalPath, "rb") as wavInput:
                params = wavInput.getparams()
                frames = wavInput.readframes(params.nframes)
            if params.sampwidth == 2:
                dataType = np.int16
            elif params.sampwidth == 1:
                dataType = np.int8
            elif params.sampwidth == 4:
                dataType = np.int32
            else:
                return originalPath
            
            audioData = np.frombuffer(frames, dtype=dataType).copy()
            amplifiedData = np.clip(audioData * gainFactor, np.iinfo(dataType).min, np.iinfo(dataType).max).astype(dataType)
            tempFile = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            self.tempWavPath = tempFile.name
            tempFile.close()
            with wave.open(self.tempWavPath, "wb") as wavOutput:
                wavOutput.setparams(params)
                wavOutput.writeframes(amplifiedData.tobytes())
            return self.tempWavPath
        
        except Exception:
            return originalPath

    def onPlaybackStateChanged(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.playPauseButton.setText("Pause")

        else:
            self.playPauseButton.setText("Play")

    def onPlaybackPositionChanged(self, positionMs):
        currentSec = positionMs / 1000.0
        if not self.playbackTimeEdit.hasFocus():
            self.playbackTimeEdit.blockSignals(True)
            self.playbackTimeEdit.setText(f"{currentSec:.2f}")
            self.playbackTimeEdit.blockSignals(False)

        if self.playheadLine is not None:
            self.playheadLine.setValue(currentSec)

    def onSliderChanged(self):
        if self.minTimeSlider.value() > self.maxTimeSlider.value():
            if self.sender() == self.minTimeSlider:
                self.maxTimeSlider.setValue(self.minTimeSlider.value())
            else:
                self.minTimeSlider.setValue(self.maxTimeSlider.value())

        self.syncEditFieldsFromSliders()
        if self.mediaPlayer.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            minSec = self.minTimeSlider.value() / 100.0
            self.mediaPlayer.setPosition(int(minSec * 1000))

        self.updatePlot()

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
        self.minTimeSlider.setValue(int(round(minSec * 100)))

        self.maxTimeSlider.blockSignals(True)
        self.maxTimeSlider.setValue(int(round(maxSec * 100)))

        self.minTimeSlider.blockSignals(False)
        self.maxTimeSlider.blockSignals(False)

        self.syncEditFieldsFromSliders()
        if self.mediaPlayer.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            self.mediaPlayer.setPosition(int(minSec * 1000))
        self.updatePlot()

    def syncEditFieldsFromSliders(self):
        minSec = self.minTimeSlider.value() / 100.0
        maxSec = self.maxTimeSlider.value() / 100.0

        self.minTimeEdit.blockSignals(True)
        self.minTimeEdit.setText(f"{minSec:.2f}")

        self.maxTimeEdit.blockSignals(True)
        self.maxTimeEdit.setText(f"{maxSec:.2f}")

        self.minTimeEdit.blockSignals(False)
        self.maxTimeEdit.blockSignals(False)

    def updatePlot(self):
        if self.currentWav is None or not self.currentWav.dataLoaded:
            self.dbCurve.setData([], [])
            self.dbRmsCurve.setData([], [])
            self.fftCurve.setData([], [])
            return
        
        showDb = self.cbShowDb.isChecked()
        showFft = self.cbShowFft.isChecked()
        
        minTime = self.minTimeSlider.value() / 100.0
        maxTime = self.maxTimeSlider.value() / 100.0

        if showDb:
            self.dbPlot.setVisible(True)
            dbData = self.currentWav.dbData
            dbRmsData = self.currentWav.dbRmsData
            
            if len(dbData) > 0:
                maskDb = (dbData[:, 0] >= minTime) & (dbData[:, 0] <= maxTime)
                self.dbCurve.setData(dbData[maskDb, 0], dbData[maskDb, 1])
            else:
                self.dbCurve.setData([], [])

            if len(dbRmsData) > 0:
                maskRms = (dbRmsData[:, 0] >= minTime) & (dbRmsData[:, 0] <= maxTime)
                self.dbRmsCurve.setData(dbRmsData[maskRms, 0], dbRmsData[maskRms, 1])
            else:
                self.dbRmsCurve.setData([], [])

            if minTime < maxTime:
                self.dbPlot.setXRange(minTime, maxTime, padding=0)
            self.dbPlot.setYRange(40, 120, padding=0)
        else:
            self.dbPlot.setVisible(False)

        if showFft:
            self.fftPlot.setVisible(True)
            sampleRate = self.currentWav.sampleRate
            data = self.currentWav.data
            timeArray = self.currentWav.timeArray
            if len(data) > 0 and sampleRate > 0:
                maskSignal = (timeArray >= minTime) & (timeArray <= maxTime)
                slicedData = data[maskSignal]
                if len(slicedData) > 0:
                    freqs, dbFS = self.currentWav.fft(slicedData)
                    # Avoid log(0) for pyqtgraph log scale plotting
                    validMask = freqs > 0
                    self.fftCurve.setData(freqs[validMask], dbFS[validMask])
                else:
                    self.fftCurve.setData([], [])
            else:
                self.fftCurve.setData([], [])

            self.fftPlot.setXRange(np.log10(10), np.log10(30000))
            self.fftPlot.setYRange(0, 80)
        else:
            self.fftPlot.setVisible(False)

    def exportPlot(self):
        if self.currentWav is None or not self.currentWav.dataLoaded:
            return

        fileName = f"{self.currentWav.testName}"

        if self.cbShowDb.isChecked and self.cbShowFft.isChecked:
            fileName += "_comboplot"
        elif self.cbShowFft.isChecked:
            fileName += "_freqplot"
        elif self.cbShowDb.isChecked:
            fileName += "_dbplot"
        fileName += ".png"
        
        filePath, _ = QFileDialog.getSaveFileName(
            self, "Save Plot",
            fileName, "PNG Image (.png)"
        )

        if filePath:
            self.plotWidget.grab().save(filePath)

    def closeEvent(self, event):
        self.mediaPlayer.stop()
        if self.tempWavPath and os.path.exists(self.tempWavPath):
            try:
                os.remove(self.tempWavPath)
            except Exception:
                pass

        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = wavWindow()
    win.show()
    sys.exit(app.exec())