import json
import csv
import time
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

# ================= CONFIGURATION =================
BROKER = "10.82.218.19"
PORT = 1883
TOPIC = "sensor/ppg"

filename = f"ppg_record_{int(time.time())}.csv"
# Membuka file dengan mode buffering minimal
csv_file = open(filename, mode="w", newline="", buffering=1)
writer = csv.writer(csv_file)
writer.writerow(["red_raw", "red_final (Filtered)", "ir_raw", "ir_final (Filtered)"])

print(f"📁 Recording to: {filename}")
print("🎧 Menunggu data... Biarkan minimal 1 menit.")

# ================= CALLBACKS =================
count = 0

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Terhubung! Menunggu aliran data...")
        client.subscribe(TOPIC, qos=0)
    else:
        print(f"❌ Gagal konek, RC: {rc}")

def on_message(client, userdata, msg):
    global count
    try:
        # Decode secepat mungkin
        payload = msg.payload.decode()
        data = json.loads(payload)
        
        # Ambil key sesuai snprintf di ESP32 (red_raw, red_filtered, ir_raw, ir_filtered)
        writer.writerow([
            data.get("red_raw", 0),
            data.get("red_filtered", 0),
            data.get("ir_raw", 0),
            data.get("ir_filtered", 0)
        ])

        count += 1
        if count % 10 == 0:
            print(f"🚀 Data Terkumpul: {count}", end='\r')
            
    except Exception:
        pass

# ================= MQTT CLIENT =================
client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

# Pengaturan Buffer Maksimal
client.max_inflight_messages_set(5000)
client.max_queued_messages_set(0)

try:
    client.connect(BROKER, PORT, keepalive=60)
    
    # loop_start menjalankan network loop di background thread
    # Ini jauh lebih stabil untuk data high-frequency (25Hz)
    client.loop_start()
    
    while True:
        time.sleep(1) # Biarkan script tetap hidup
        
except KeyboardInterrupt:
    print(f"\n🛑 Berhenti manual. Total: {count}")
finally:
    client.loop_stop()
    csv_file.flush()
    csv_file.close()
    print(f"✅ Selesai. Total data: {count}")
    