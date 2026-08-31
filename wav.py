#using scipy, get fourier and db plot
from scipy.io import wavfile
from scipy.fft import rfft, rfftfreq
import glob
import os
import readline
import scipy.io
import matplotlib.pyplot as plt
import numpy as np

path = "Tests"
os.chdir(path)

def complete_filename(text, state):
    return (glob.glob(text+'*.wav')+[None])[state]

while True:
    #tab completion
    readline.set_completer_delims(' \t\n;')
    readline.parse_and_bind("tab: complete")
    readline.set_completer(complete_filename)
    Fname = input("\n Input file name: ")

    samplerate, data = wavfile.read(Fname)

    print(f"Sampled at {samplerate}Hz")

    length = data.shape[0] / samplerate
    print(f"Recording is {length:.2f}s")


    fig1 = plt.figure()
    #normalize audio data
    dataNorm = data / 2147483648.0

    #avoid log 0 via epsilon
    epsilon = 1e-10
    db = 20 * np.log10(np.abs(dataNorm) + epsilon)

    dbMax = max(db)

    print(f"Max dBFS is {dbMax:.2f} dBFS")

    time = np.linspace(0., length, data.shape[0])
    plt.plot(time, db)
    plt.title("dB versus Time")
    plt.xlabel("Time [s]")
    plt.ylabel("dBFS")
    plt.ylim(-100, 0)

    fig2 = plt.figure()

    fft_spectrum = rfft(data)
    magnitude = np.abs(fft_spectrum)

    frequencies = rfftfreq(len(data), d=1/samplerate)

    index = np.argmax(magnitude)
    freqMax = frequencies[index]

    print(f"Most signifigant frequency is {freqMax:.2f} Hz")

    plt.plot(frequencies, magnitude, color='blue')
    plt.title("Frequency vs Magnitude")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude")
    plt.xscale('log')
    plt.xlim(1, 44000)

    plt.show()