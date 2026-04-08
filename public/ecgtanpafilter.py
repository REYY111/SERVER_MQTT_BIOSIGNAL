import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import json
import csv
import os

# ================= CONFIG =================
MQTT_BROKER = "192.168.0.102"
TOPIC_SUB = "sensor/biosignal"
TOPIC_PUB = "sensor/ecg_raw_only"

# ================= AUTO CSV FILE =================
def get_next_filename():
    base = "ecg_log_tes"
    i = 1
    while os.path.exists(f"{base}_{i}.csv"):
        i += 1
    return f"{base}_{i}.csv"

CSV_FILE = get_next_filename()

# Header CSV ECG
with open(CSV_FILE, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["ecg_ts", "ecg", "bpm", "leadOff"])

# ================= MQTT CALLBACK =================
def on_message(client, userdata, msg):
    try:
        raw_payload = msg.payload.decode().strip()
        
        # Fix format JSON dari ESP32
        if not raw_payload.startswith('{'):
            raw_payload = "{" + raw_payload + "}"
        
        if raw_payload.count('{') > 1:
            raw_payload = "{" + raw_payload.split('{')[-1].split('}')[0] + "}"
        
        data = json.loads(raw_payload)

        # Ambil data ECG
        if "ecg" in data:
            val_ecg   = data["ecg"]
            val_bpm   = data.get("bpm", 0)
            val_lead  = data.get("leadOff", 0)
            ts        = data.get("ecg_ts", 0)

            result = {
                "ecg": val_ecg,
                "bpm": val_bpm,
                "leadOff": val_lead,
                "ecg_ts": ts
            }

            # 1. Publish ulang (buat dashboard)
            client.publish(TOPIC_PUB, json.dumps(result))

            # 2. Simpan ke CSV
            with open(CSV_FILE, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([ts, val_ecg, val_bpm, val_lead])

            # 3. Print realtime
            print(f"❤️ ECG -> Val: {val_ecg} | BPM: {val_bpm} | TS: {ts}")

    except Exception as e:
        pass

# ================= CONNECT =================
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"✅ Terkoneksi ke Broker {MQTT_BROKER}!")
        client.subscribe(TOPIC_SUB)
    else:
        print(f"❌ Gagal konek, kode: {rc}")

# ================= SETUP MQTT =================
client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(MQTT_BROKER, 1883, 60)
except Exception as e:
    print(f"❌ Broker tidak terjangkau: {e}")
    exit()

print(f"🚀 ECG LOGGER ACTIVE | File: {CSV_FILE}")
print("Tekan Ctrl+C untuk berhenti.")

try:
    client.loop_forever()
except KeyboardInterrupt:
    print(f"\n💾 Logging berhenti. Data tersimpan di {CSV_FILE}")