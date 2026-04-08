import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import json
import csv
import os

# ================= CONFIG =================
MQTT_BROKER = "192.168.0.102"
TOPIC_SUB = "sensor/biosignal"
TOPIC_PUB = "sensor/emg_raw_only"

def get_next_filename():
    base = "emg_raw_log"
    i = 1
    while os.path.exists(f"{base}_{i}.csv"):
        i += 1
    return f"{base}_{i}.csv"

CSV_FILE = get_next_filename()

# Simpan file object agar tidak open-close setiap milidetik (Optimasi High Speed)
csv_handle = open(CSV_FILE, mode='w', newline='')
writer = csv.writer(csv_handle)
writer.writerow(["emg_ts", "raw", "clean", "envelope"])

# ================= MQTT CALLBACK =================
def on_message(client, userdata, msg):
    try:
        raw_payload = msg.payload.decode().strip()
        data = json.loads(raw_payload)

        # 1. CEK DATA EMG_RAW (BATCH DARI CIRCULAR BUFFER)
        if "emg_raw" in data and isinstance(data["emg_raw"], list):
            emg_batch = data["emg_raw"]
            ts_end = data["emg_ts"] 
            batch_size = len(emg_batch)

            # 2. UNPACKING KE CSV (Sangat Cepat)
            for i, val in enumerate(emg_batch):
                # Rekonstruksi timestamp (asumsi 1ms per data)
                current_ts = ts_end - (batch_size - 1 - i)
                writer.writerow([current_ts, val, val, val])
            
            # Flush data ke disk setiap batch agar tidak hilang jika crash
            csv_handle.flush()

            # 3. MONITORING TERMINAL
            # Kita hanya print sesekali (sampling terminal) agar tidak membebani CPU
            # Misal: hanya jika ts_end genap kelipatan 100
            if ts_end % 50 == 0:
                lead_status = "⚠️ LEAOFF" if data.get("leadOff") == 1 else "✅ OK"
                print(f"📥 Batch In -> Last Val: {emg_batch[-1]} | TS: {ts_end} | Sensor: {lead_status}")

            # 4. RE-PUBLISH UNTUK DASHBOARD
            client.publish(TOPIC_PUB, json.dumps({"raw": emg_batch[-1], "ts": ts_end}))

    except Exception as e:
        # print(f"Parsing Error: {e}")
        pass

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"✅ MQTT Connected! Logging ke: {CSV_FILE}")
        client.subscribe(TOPIC_SUB)
    else:
        print(f"❌ Connection Failed, code: {rc}")

# ================= RUNNER =================
client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

try:
    print(f"🚀 Logger Aktif di {MQTT_BROKER}...")
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_forever()
except KeyboardInterrupt:
    print(f"\n💾 Menutup file dan menyimpan data...")
finally:
    csv_handle.close()
    print(f"✅ Data aman di {CSV_FILE}")