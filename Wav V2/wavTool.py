import os
import json
import numpy as np
import numpy.typing as npt
from scipy.io import wavfile
from scipy.fft import rfft, rfftfreq

class wavTool:
    def __init__(self, testPath: str = ""):
        self.testName = ""
        self.testPath = ""
        self.sampleRate = 0
        self.data = np.array([])
        self.timeArray = np.array([])
        self.dbData = np.array([])
        self.dbRmsData = np.array([])
        self.testSuccess = False
        self.dataLoaded = False
        self.minTime = 0.0
        self.maxTime = 0.0
        self.totalDuration = 0.0

        if testPath:
            self.loadTest(testPath)

    #get test data
    def loadTest(self, testPath: str):
        self.testPath = testPath
        self.testName = os.path.basename(os.path.normpath(testPath))
        self.getTestInfo(testPath)
        
        self.wavDecode(testPath)
        
        if self.dataLoaded:
            self.dbData, self.dbRmsData = self.dbDecode(self.data)

    #read TestTime json (min / max time & test success)
    def getTestInfo(self, testPath: str):
        jsonPath = os.path.join(testPath, "TestTime.json")
        if os.path.exists(jsonPath):
            try:
                with open(jsonPath, "r") as jsonFile:
                    info = json.load(jsonFile)
                    self.testSuccess = info.get("TestSuccess", False)
                    self.minTime = float(info.get("MinTime", 0))
                    self.maxTime = float(info.get("MaxTime", 0))
            except Exception:
                self.testSuccess = False
                self.minTime = 0.0
                self.maxTime = 0.0
        else:
            self.testSuccess = False
            self.minTime = 0.0
            self.maxTime = 0.0

    #decode wav
    def wavDecode(self, testPath: str):
        folderName = os.path.basename(os.path.normpath(testPath))
        wavPath = os.path.join(testPath, f"{folderName}.wav")
        
        if not os.path.exists(wavPath):
            self.dataLoaded = False
            raise FileNotFoundError(f"WAV file not found: {wavPath}")

        try:
            self.sampleRate, rawData = wavfile.read(wavPath)
            if rawData.size == 0:
                self.dataLoaded = False
                raise ValueError("WAV file is empty")

            #stereo audio
            if rawData.ndim > 1:
                rawData = rawData[:, 0]

            #normalize data
            if rawData.dtype == np.int16:
                normalizedData = rawData / 32768.0
            elif rawData.dtype == np.int32:
                normalizedData = rawData / 2147483648.0
            elif rawData.dtype == np.uint8:
                normalizedData = (rawData - 128.0) / 128.0
            else:
                normalizedData = rawData.astype(np.float64)

            self.data = normalizedData
            self.totalDuration = len(self.data) / self.sampleRate if self.sampleRate > 0 else 0
            self.timeArray = np.linspace(0, self.totalDuration, len(self.data), endpoint=False)

            if self.maxTime == 0.0 or self.maxTime > self.totalDuration:
                self.maxTime = self.totalDuration

            self.dataLoaded = True

        except Exception as e:
            self.dataLoaded = False
            raise e

    #get dB data
    def dbDecode(self, data: npt.ArrayLike) -> tuple[npt.ArrayLike, npt.ArrayLike]:
        eps = 1e-12
        absData = np.abs(data) + eps
        dbSignal = 20 * np.log10(absData) + 142

        timeValArray = np.column_stack((self.timeArray, data))
        rmsArray = self.rollingAverage(timeValArray)

        rmsVals = np.abs(rmsArray[:, 1]) + eps
        dbRmsSignal = 20 * np.log10(rmsVals) + 142
        rmsTimeArray = rmsArray[:, 0]

        dbData = np.column_stack((self.timeArray, dbSignal))
        dbRmsData = np.column_stack((rmsTimeArray, dbRmsSignal))
        return dbData, dbRmsData

    #get FFT data
    def fft(self, data: npt.ArrayLike) -> tuple[npt.ArrayLike, npt.ArrayLike]:
        """Calculates single-sided FFT spectrum and converts magnitude to dBFS."""
        if len(data) == 0 or self.sampleRate == 0:
            return np.array([]), np.array([])

        fftValues = rfft(data)
        fftFreqs = rfftfreq(len(data), 1.0 / self.sampleRate)
        
        fftMagnitude = np.abs(fftValues) * 2.0 / len(data)
        
        #magnitude to dBFS
        eps = 1e-12
        fftDbFS = 20 * np.log10(np.maximum(fftMagnitude, eps)) + 142
        return fftFreqs, fftDbFS

    #calculate dBFS RMS
    def rollingAverage(self, arr: npt.ArrayLike) -> npt.ArrayLike:
        sampleWindow = 0.010  #10ms RMS window
        time = arr[:, 0]
        vals = arr[:, 1]
        samples = len(time)
        if samples < 2:
            return arr

        aTPS = (np.max(time) - np.min(time)) / samples
        numSPW = max(1, round(sampleWindow / aTPS))

        valsSquar = vals ** 2
        kernel = np.ones(numSPW)
        sumSquar = np.convolve(valsSquar, kernel, mode="valid")
        rmsVals = np.sqrt(sumSquar / numSPW)
        offset = numSPW // 2

        time = time[offset : offset + len(rmsVals)]
        return np.column_stack((time, rmsVals))