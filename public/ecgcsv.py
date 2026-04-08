import serial
import csv
import time

# ================= SERIAL =================
ser = serial.Serial('COM12', 115200)  # ganti COM sesuai ESP32
time.sleep(2)  # tunggu ESP32 reset

# ================= FILE CSV =================
filename = f"ecg_data_{int(time.time())}.csv"
csv_file = open(filename, mode="w", newline="")
writer = csv.writer(csv_file)

# header CSV
writer.writerow(["pc_time_ms", "ECG_value", "BPM"])

start_time = time.time()
print(f"📁 Recording to {filename}...")

try:
    while True:
        line = ser.readline().decode('utf-8').strip()
        if line:
            # contoh Serial print: "ECG:1450 BPM:72 LeadOff:0"
            parts = line.replace("ECG:", "").replace("BPM:", "").split()
            if len(parts) >= 2:
                ecg = int(parts[0])
                bpm = int(parts[1])
                pc_time = int((time.time() - start_time) * 1000)
                writer.writerow([pc_time, ecg, bpm])
                csv_file.flush()
                print([pc_time, ecg, bpm])
except KeyboardInterrupt:
    print("\n🛑 Recording stopped")
    csv_file.close()
    ser.close()