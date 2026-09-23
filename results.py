import os
import json
import re
from datetime import datetime
import numpy as np
import numpy.typing as npt
from scipy.io import wavfile
from scipy.fft import rfft, rfftfreq
import math

def parse_test_inputs(input_str):
    """
    Parses strings like 'TXX', 'TXX-TXX', or 'TXX, TXX, TXX-TXX' into a sorted list of unique test labels
    """
    test_set = set()
    tokens = re.split(r'[, ]+', input_str.strip().upper())
    
    for token in tokens:
        if not token:
            continue
        
        range_match = re.match(r"^T(\d+)\s*-\s*T?(\d+)$", token)
        single_match = re.match(r"^T(\d+)$", token)
        
        if range_match:
            start_num = int(range_match.group(1))
            end_num = int(range_match.group(2))
            
            padding_width = max(len(range_match.group(1)), len(range_match.group(2)))
            
            step = 1 if start_num <= end_num else -1
            for num in range(start_num, end_num + step, step):
                test_set.add(f"T{num:0{padding_width}d}")
                
        elif single_match:
            num = int(single_match.group(1))
            padding_width = len(single_match.group(1))
            test_set.add(f"T{num:0{padding_width}d}")
        else:
            print(f"Warning: Could not parse token '{token}'. Skipping.")
            
    return sorted(list(test_set))

def normalize_audio(data):
    if np.issubdtype(data.dtype, np.integer):
        max_val = float(np.iinfo(data.dtype).max)
        return data.astype(np.float64) / max_val
    return data.astype(np.float64)

def process_test(test_no, base_dir="Tests"):
    test_folder = os.path.join(base_dir, test_no)
    json_path = os.path.join(test_folder, "TestTime.json")
    wav_path = os.path.join(test_folder, f"{test_no}.wav")

    if not os.path.exists(json_path):
        print(f"[-] {test_no}: Missing TestTime.json")
        return None

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            time_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[-] {test_no}: Invalid JSON formatting ({e})")
        return None

    if not time_data.get('TestSuccess', False):
        print(f"[-] {test_no}: Skipped (Test failed)")
        return None

    if not os.path.exists(wav_path):
        print(f"[-] {test_no}: Missing audio file ({test_no}.wav)")
        return None

    min_time = time_data.get('MinTime', 0.0)
    max_time = time_data.get('MaxTime', 99)

    if min_time >= max_time:
        print(f"[-] {test_no}: Invalid time slicing parameters")
        return None

    dbArray, dbRMS, freqArray = wavDecode(wav_path, min_time, max_time)

    print("TEST")
    print(freqArray[np.argmax(freqArray[:, 0]):, 1])

    return {
        "TestNumber": test_no,
        "Description": "",
        "MaxdBFS": round(max(dbArray[:, 1]), 2),
        "dBFSrms": round(max(dbRMS[:, 1]), 2),
        "SignificantFrequencyHz": round(max(freqArray[:, 0]), 2),
        "FrequencyAmplitude": round(freqArray[np.argmax(freqArray[:, 0]):, 1].item(), 2)
    }

@staticmethod
def wavDecode(Fname:str, start:int, end:int) -> tuple[npt.ArrayLike, npt.ArrayLike, npt.ArrayLike]:
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

        dbMax = max(db)

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
        sumSquar = np.convolve(valsSquar, kernel, mode="valid")  #convolving is complicated but 
        rmsVals = np.sqrt(sumSquar / numSPW)
        offset = numSPW // 2

        time = time[offset : offset + len(rmsVals)] #trim time to exclude the un-rms-able values
        return np.column_stack((time, -rmsVals))

def main():
    base_dir = "Tests"
    if not os.path.exists(base_dir):
        print(f"Error: Directory '{base_dir}' not found.")
        return

    print("=== Test Results Collector ===")
    user_input = input("Enter test numbers/ranges (e.g. TXX, TXX-TXX): ").strip()

    tests_to_process = parse_test_inputs(user_input)

    if not tests_to_process:
        print("No valid tests entered. Exiting.")
        return

    print(f"\nQueueing {len(tests_to_process)} test(s): {', '.join(tests_to_process)}")

    # output
    results = []
    print("\nProcessing...")
    for test_no in tests_to_process:
        res = process_test(test_no, base_dir=base_dir)
        if res:
            results.append(res)
            print(f"[+] {test_no}: Success | Max dBFS: {res['MaxdBFS']} dBFS | Peak Freq: {res['SignificantFrequencyHz']} Hz")

    output_dir = "Results"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%H-%M-%S-%m-%d-%Y")
    output_filename = f"results-{timestamp}.json"
    
    output_filepath = os.path.join(output_dir, output_filename)

    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)

    print(f"\nFinished. Saved {len(results)} successful result(s) to '{output_filepath}'.")

if __name__ == "__main__":
    main()