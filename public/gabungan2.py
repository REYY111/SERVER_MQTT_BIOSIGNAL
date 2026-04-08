import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import numpy as np
import json
from scipy.signal import butter, filtfilt, find_peaks

# ================= CONFIG =================
MQTT_BROKER = "192.168.0.102" 
TOPIC_SUB = "sensor/biosignal"
TOPIC_EMG_PUB = "sensor/emg_processed"
TOPIC_PPG_PUB = "sensor/ppg_processed"

FS_PPG = 75  # Disamakan dengan kFs di ppg.h ESP32 kamu
WINDOW_SIZE = 150 # 2 detik data untuk kestabilan
last_valid_bpm = 0.0

# ================= BUFFERS =================
buffer_red_raw, buffer_ir_raw = [], []
buffer_red_ac, buffer_ir_ac = [], []
buffer_emg_clean = []

def butter_filter_ppg(data):
    if len(data) < 30: return data
    # Bandpass 0.5Hz - 4Hz
    low, high = 0.5 / (FS_PPG / 2), 4.0 / (FS_PPG / 2)
    b, a = butter(2, [low, high], btype='band')
    return filtfilt(b, a, data)

def compute_bpm(ir_signal):
    global last_valid_bpm
    if len(ir_signal) < 50: return last_valid_bpm
    
    # Normalisasi
    sig_norm = (ir_signal - np.mean(ir_signal)) / (np.std(ir_signal) + 1e-6)
    
    # Mencari puncak (Distance disesuaikan dengan FS=75)
    # Minimal 0.5 detik antar detak (120 BPM) -> 75 * 0.5 = 37.5
    peaks, _ = find_peaks(sig_norm, distance=35, prominence=0.4)
    
    if len(peaks) < 2: return last_valid_bpm
    
    bpm_new = 60 / np.mean(np.diff(peaks) / FS_PPG)
    
    if 45 < bpm_new < 160:
        if last_valid_bpm == 0: last_valid_bpm = bpm_new
        last_valid_bpm = (last_valid_bpm * 0.8) + (bpm_new * 0.2)
    
    return last_valid_bpm

def compute_spo2(red_raw, ir_raw, red_f, ir_f):
    if len(red_raw) < 10: return 0
    dc_red, dc_ir = np.mean(red_raw), np.mean(ir_raw)
    ac_red, ac_ir = np.std(red_f), np.std(ir_f)
    if dc_red == 0 or dc_ir == 0 or ac_ir == 0: return 0
    R = (ac_red / dc_red) / (ac_ir / dc_ir)
    spo2 = 110 - 18 * R
    return min(100.0, max(80.0, spo2))

# ================= CALLBACK MQTT =================
counter_update = 0

def on_message(client, userdata, msg):
    global buffer_red_raw, buffer_ir_raw, buffer_red_ac, buffer_ir_ac, buffer_emg_clean, counter_update

    try:
        payload = msg.payload.decode().strip()
        data = json.loads(payload)
        
        # 1. PROSES EMG (Mendukung data array dari ESP32)
        rms = 0.0
        if "emg_raw" in data:
            emg_vals = data["emg_raw"]
            # Masukkan semua batch data ke buffer
            for v in emg_vals:
                buffer_emg_clean.append(v)
            
            # Batasi buffer 100 sampel
            if len(buffer_emg_clean) > 100: 
                buffer_emg_clean = buffer_emg_clean[-100:]
            
            rms = np.sqrt(np.mean(np.array(buffer_emg_clean)**2))
            
            # Publish hasil EMG
            client.publish(TOPIC_EMG_PUB, json.dumps({
                "raw_emg": emg_vals[-1],
                "clean_emg": round(float(emg_vals[-1]), 2),
                "rms_emg": round(float(rms), 3)
            }))

        # 2. PROSES PPG
        if "red_raw" in data:
            buffer_red_raw.append(data["red_raw"])
            buffer_ir_raw.append(data["ir_raw"])
            
            # Gunakan data yang sudah difilter ringan dari ESP32
            buffer_red_ac.append(data.get("red_filtered", data["red_raw"]))
            buffer_ir_ac.append(data.get("ir_filtered", data["ir_raw"]))

            if len(buffer_red_raw) > WINDOW_SIZE:
                buffer_red_raw.pop(0); buffer_ir_raw.pop(0)
                buffer_red_ac.pop(0); buffer_ir_ac.pop(0)

            counter_update += 1
            # Update output setiap 10 data baru (~130ms)
            if len(buffer_red_raw) >= WINDOW_SIZE and counter_update >= 10:
                counter_update = 0
                
                # Filter ulang agar sinyal sangat bersih untuk BPM
                red_f = butter_filter_ppg(buffer_red_ac)
                ir_f  = butter_filter_ppg(buffer_ir_ac)
                
                bpm   = compute_bpm(ir_f)
                spo2  = compute_spo2(buffer_red_raw, buffer_ir_raw, red_f, ir_f)

                client.publish(TOPIC_PPG_PUB, json.dumps({
                    "bpm": round(bpm, 1),
                    "spo2": round(spo2, 1),
                    "red_filtered": round(red_f[-1], 2),
                    "ir_filtered": round(ir_f[-1], 2),
                    "ts": data.get("ppg_ts", 0)
                }))
                
                status_emg = f"RMS: {round(rms,2)}" if rms > 0 else "EMG: OFF"
                print(f"💓 BPM: {round(bpm,1)} | 🩸 SpO2: {round(spo2,1)}% | 💪 {status_emg}")

    except Exception as e:
        print(f"⚠️ Error: {e}")

# ================= SETUP =================
client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
client.on_message = on_message

print(f"🔍 Connecting to Broker {MQTT_BROKER}...")
try:
    client.connect(MQTT_BROKER, 1883, 60)
except Exception as e:
    print(f"❌ Connection Failed: {e}")
    exit()

client.subscribe(TOPIC_SUB)
print(f"🚀 PROCESSOR ACTIVE (PPG & EMG)")
client.loop_forever()