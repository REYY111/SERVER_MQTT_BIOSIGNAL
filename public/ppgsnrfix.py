import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import numpy as np
import json
import csv
import os
from scipy.signal import butter, filtfilt, find_peaks

# ================= CONFIG =================
MQTT_BROKER = "10.103.158.19"
TOPIC_SUB = "sensor/biosignal"
TOPIC_PUB = "sensor/ppg_processed"

FS = 50 
WINDOW = 100 
last_valid_bpm = 0.0

# ================= BUFFER =================
buffer_red_raw = []
buffer_ir_raw  = []
buffer_red_ac  = []
buffer_ir_ac   = []

# ================= AUTO CSV FILE =================
def get_next_filename():
    base = "ppg_log"
    i = 1
    while os.path.exists(f"{base}_{i}.csv"):
        i += 1
    return f"{base}_{i}.csv"

CSV_FILE = get_next_filename()

with open(CSV_FILE, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["ts", "red_raw", "ir_raw", "red_f", "ir_f", "bpm", "spo2"])

# ================= FILTER =================
def butter_filter(data):
    if len(data) < 15: return data
    low = 0.5 / (FS / 2)
    high = 4.0 / (FS / 2)
    b, a = butter(2, [low, high], btype='band')
    # Gunakan padlen untuk menghindari error jika data pendek
    return filtfilt(b, a, data, padlen=min(len(data)-1, 15))

# ================= BPM =================
def compute_bpm(ir_signal):
    global last_valid_bpm
    if len(ir_signal) < 40: return last_valid_bpm

    sig_norm = (ir_signal - np.mean(ir_signal)) / (np.std(ir_signal) + 1e-6)
    peaks, _ = find_peaks(sig_norm, distance=FS*0.5, prominence=0.4)

    if len(peaks) < 2: return last_valid_bpm

    intervals = np.diff(peaks) / FS
    bpm_instant = 60 / np.mean(intervals)

    if 45 < bpm_instant < 160:
        if last_valid_bpm == 0: last_valid_bpm = bpm_instant
        else: last_valid_bpm = (last_valid_bpm * 0.8) + (bpm_instant * 0.2)
            
    return last_valid_bpm

# ================= SPO2 =================
def compute_spo2(red_raw, ir_raw, red_f, ir_f):
    if len(red_raw) < 10: return 0
    dc_red, dc_ir = np.mean(red_raw), np.mean(ir_raw)
    ac_red, ac_ir = np.std(red_f), np.std(ir_f)

    if dc_red == 0 or dc_ir == 0 or ac_ir == 0: return 0
    R = (ac_red / dc_red) / (ac_ir / dc_ir)
    spo2 = 110 - 18 * R 
    return min(100, max(0, spo2))

# ================= MQTT CALLBACK =================
def on_message(client, userdata, msg):
    global buffer_red_raw, buffer_ir_raw, buffer_red_ac, buffer_ir_ac

    try:
        raw_payload = msg.payload.decode().strip()
        
        # Perbaikan: Tangani jika ada karakter aneh di payload
        # Menghapus bracket berlebih jika ada
        if raw_payload.count('{') > 1:
            raw_payload = "{" + raw_payload.split('{')[-1].split('}')[0] + "}"
        
        data = json.loads(raw_payload)

        # Cek apakah kunci ppg ada dalam JSON (karena kamu kirim gabungan EMG & PPG)
        if "red_raw" in data:
            red_r = data["red_raw"]
            ir_r  = data["ir_raw"]
            red_f_esp = data.get("red_filtered", red_r)
            ir_f_esp  = data.get("ir_filtered", ir_r)
            ts = data.get("ppg_ts", 0)

            # Update Buffer
            buffer_red_raw.append(red_r)
            buffer_ir_raw.append(ir_r)
            buffer_red_ac.append(red_f_esp)
            buffer_ir_ac.append(ir_f_esp)

            if len(buffer_red_raw) > WINDOW:
                buffer_red_raw.pop(0)
                buffer_ir_raw.pop(0)
                buffer_red_ac.pop(0)
                buffer_ir_ac.pop(0)

            # Proses setiap kali buffer terkumpul cukup
            if len(buffer_red_raw) >= 50:
                red_f = butter_filter(buffer_red_ac)
                ir_f  = butter_filter(buffer_ir_ac)
                bpm   = compute_bpm(ir_f)
                spo2  = compute_spo2(buffer_red_raw, buffer_ir_raw, red_f, ir_f)

                # Output
                result = {
                    "bpm": round(bpm, 1),
                    "spo2": round(spo2, 1),
                    "red_filtered": round(red_f[-1], 2),
                    "ir_filtered": round(ir_f[-1], 2),
                    "ts": ts
                }

                client.publish(TOPIC_PUB, json.dumps(result))

                # Log CSV
                with open(CSV_FILE, mode='a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([ts, red_r, ir_r, result["red_filtered"], result["ir_filtered"], result["bpm"], result["spo2"]])

                print(f"💓 BPM: {result['bpm']} | 🩸 SpO2: {result['spo2']}% | TS: {ts}")

    except Exception as e:
        # Cetak error tapi jangan stop program
        print(f"⚠️ Data Error: {e} | Payload: {msg.payload.decode()[:50]}...")

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Terkoneksi ke Broker!")
        client.subscribe(TOPIC_SUB)
    else:
        print(f"❌ Gagal konek, kode: {rc}")

# ================= SETUP MQTT =================
client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

print(f"🔍 Menghubungkan ke {MQTT_BROKER}...")
try:
    client.connect(MQTT_BROKER, 1883, 60)
except Exception as e:
    print(f"❌ Broker tidak terjangkau: {e}")
    exit()

print(f"🚀 PPG PROCESSOR ACTIVE | Logging: {CSV_FILE}")
client.loop_forever()