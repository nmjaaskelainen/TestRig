import os
import json
import re
from datetime import datetime
import numpy as np
from scipy.io import wavfile
from scipy.fft import rfft, rfftfreq

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

    # if not time_data.get('TestSuccess', False):
    #     print(f"[-] {test_no}: Skipped (Test failed)")
    #     return None

    if not os.path.exists(wav_path):
        print(f"[-] {test_no}: Missing audio file ({test_no}.wav)")
        return None

    samplerate, raw_data = wavfile.read(wav_path)

    if raw_data.ndim > 1:
        raw_data = raw_data.mean(axis=1)

    min_time = time_data.get('MinTime', 0.0)
    max_time = time_data.get('MaxTime', raw_data.shape[0] / samplerate)

    start_sample = max(0, int(min_time * samplerate))
    end_sample = min(len(raw_data), int(max_time * samplerate))
    
    if start_sample >= end_sample:
        print(f"[-] {test_no}: Invalid time slicing parameters")
        return None

    sliced_data = raw_data[start_sample:end_sample]

    # db
    data_norm = normalize_audio(sliced_data)
    epsilon = 1e-10
    db_series = 20 * np.log10(np.abs(data_norm) + epsilon)
    max_dbfs = float(np.max(db_series))

    # fft
    fft_spectrum = rfft(data_norm)
    magnitude = np.abs(fft_spectrum)
    frequencies = rfftfreq(len(data_norm), d=1.0 / samplerate)

    peak_idx = np.argmax(magnitude)
    peak_freq = float(frequencies[peak_idx])
    peak_amplitude = float(magnitude[peak_idx])

    return {
        "TestNumber": test_no,
        "Description": "",
        "MaxdBFS": round(max_dbfs, 2),
        "SignificantFrequencyHz": round(peak_freq, 2),
        "FrequencyAmplitude": round(peak_amplitude, 2)
    }

def main():
    base_dir = "Tests"
    if not os.path.exists(base_dir):
        print(f"Error: Directory '{base_dir}' not found.")
        return

    print("=== Test Results Collector ===")
    user_input = input("Enter test numbers/ranges (e.g. T01, T07-T19): ").strip()

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