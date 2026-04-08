import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import json
import csv
import os

# ================= CONFIG =================
MQTT_BROKER = "192.168.0.102"
TOPIC_SUB = "sensor/biosignal"
TOPIC_PUB = "sensor/ppg_raw_only"

# ================= AUTO CSV FILE =================
def get_next_filename():
    base = "ppg_raw_log_led"
    i = 1
    while os.path.exists(f"{base}_{i}.csv"):
        i += 1
    return f"{base}_{i}.csv"

CSV_FILE = get_next_filename()

# 🔥 TAMBAH led_current di header
with open(CSV_FILE, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["ts", "red_raw", "ir_raw", "led_current"])

# ================= MQTT CALLBACK =================
def on_message(client, userdata, msg):
    try:
        raw_payload = msg.payload.decode().strip()
        
        # Handle payload aneh (double bracket)
        if raw_payload.count('{') > 1:
            raw_payload = "{" + raw_payload.split('{')[-1].split('}')[0] + "}"
        
        data = json.loads(raw_payload)

        if "red_raw" in data:
            red_r = data["red_raw"]
            ir_r  = data["ir_raw"]
            ts    = data.get("ts", data.get("ppg_ts", 0))

            # 🔥 AMBIL LED CURRENT
            led = data.get("led_current", -1)  # -1 kalau ga ada

            # Result JSON baru
            result = {
                "red_raw": red_r,
                "ir_raw": ir_r,
                "led_current": led,
                "ts": ts
            }

            # 1. Publish ulang
            client.publish(TOPIC_PUB, json.dumps(result))

            # 2. Simpan ke CSV
            with open(CSV_FILE, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([ts, red_r, ir_r, led])

            # 3. Print monitoring
            print(f"📊 RAW -> Red:{red_r} | IR:{ir_r} | LED:{led} | TS:{ts}")

    except Exception as e:
        print(f"⚠️ Data Error: {e}")

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

print(f"🚀 RAW LOGGER + LED ACTIVE | File: {CSV_FILE}")
client.loop_forever()