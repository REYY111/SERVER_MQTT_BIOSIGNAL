import serial
import numpy as np
import csv
import os
import time
from scipy.signal import find_peaks

# ================= CONFIG =================
SERIAL_PORT = "COM12"  # <--- UBAH INI (Contoh: COM3 atau /dev/ttyUSB0)
BAUD_RATE = 115200
FS = 50 
WINDOW = 100 

# Global state
last_valid_bpm = 0.0
last_valid_spo2 = 100.0

# Buffers
buf_red_raw, buf_ir_raw, buf_red_f, buf_ir_f = [], [], [], []

def get_next_filename():
    base = "ppg_log"
    i = 1
    while os.path.exists(f"{base}_{i}.csv"): i += 1
    return f"{base}_{i}.csv"

CSV_FILE = get_next_filename()

with open(CSV_FILE, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["ts", "red_raw", "ir_raw", "red_f", "ir_f", "bpm", "spo2"])

def calculate_metrics(ir_f, red_raw, ir_raw, red_f):
    global last_valid_bpm, last_valid_spo2
    
    # BPM Calculation
    sig_norm = (ir_f - np.mean(ir_f)) / (np.std(ir_f) + 1e-6)
    peaks, _ = find_peaks(sig_norm, distance=FS*0.5, prominence=0.4)
    bpm = last_valid_bpm
    if len(peaks) >= 2:
        bpm_inst = 60 / (np.mean(np.diff(peaks)) / FS)
        if 45 < bpm_inst < 160:
            bpm = (last_valid_bpm * 0.7 + bpm_inst * 0.3) if last_valid_bpm > 0 else bpm_inst
            last_valid_bpm = bpm

    # SpO2 Calculation (R-Ratio)
    dc_red, dc_ir = np.mean(red_raw), np.mean(ir_raw)
    ac_red, ac_ir = np.std(red_f), np.std(ir_f)
    spo2 = last_valid_spo2
    if dc_red > 0 and dc_ir > 0 and ac_ir > 0:
        R = (ac_red / dc_red) / (ac_ir / dc_ir)
        spo2_inst = 110 - 18 * R
        spo2_inst = min(100, max(70, spo2_inst))
        spo2 = (last_valid_spo2 * 0.9 + spo2_inst * 0.1)
        last_valid_spo2 = spo2
        
    return round(bpm, 1), round(spo2, 1)

# ================= MAIN LOOP =================
print(f"🔍 Mencoba membuka {SERIAL_PORT}...")
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    start_time = int(time.time() * 1000)
    print(f"🚀 Logger Aktif! Simpan ke: {CSV_FILE}")
except Exception as e:
    print(f"❌ Gagal: {e}"); exit()

try:
    while True:
        if ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8').strip()
                if not line or "," not in line: continue
                
                parts = [float(x) for x in line.split(',')]
                if len(parts) == 4:
                    r_raw, i_raw, r_f, i_f = parts
                    ts = int(time.time() * 1000) - start_time

                    # Buffer Management
                    buf_red_raw.append(r_raw); buf_ir_raw.append(i_raw)
                    buf_red_f.append(r_f); buf_ir_f.append(i_f)
                    if len(buf_red_raw) > WINDOW:
                        [b.pop(0) for b in [buf_red_raw, buf_ir_raw, buf_red_f, buf_ir_f]]

                    # Calculate & Save
                    bpm, spo2 = (0.0, 100.0)
                    if len(buf_ir_f) >= 50:
                        bpm, spo2 = calculate_metrics(np.array(buf_ir_f), np.array(buf_red_raw), 
                                                     np.array(buf_ir_raw), np.array(buf_red_f))

                    with open(CSV_FILE, mode='a', newline='') as f:
                        csv.writer(f).writerow([ts, r_raw, i_raw, r_f, i_f, bpm, spo2])
                    
                    print(f"TS: {ts} | BPM: {bpm} | SpO2: {spo2}% | IR_F: {i_f}")

            except Exception: continue
except KeyboardInterrupt:
    print(f"\n✅ Selesai. Data di {CSV_FILE}")
finally:
    ser.close()