import json
import csv
import time
import paho.mqtt.client as mqtt

# ================= MQTT =================
BROKER = "10.170.222.19"  # IP broker MQTT
PORT = 1883
TOPIC = "sensor/ecg"

# ================= FILE =================
filename = f"ecg_record_{int(time.time())}.csv"

csv_file = open(filename, mode="w", newline="")
writer = csv.writer(csv_file)

# header CSV
writer.writerow([
    "pc_time_ms",
    "ecg",
    "bpm",
    "leadOff",
    "ts"
])

csv_file.flush()

print("📁 Recording to:", filename)

# ================= CALLBACK =================
start_time = time.time()

def on_connect(client, userdata, flags, rc):
    print("✅ MQTT Connected")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    global csv_file
    try:
        data = json.loads(msg.payload.decode())

        pc_time = int((time.time() - start_time) * 1000)

        row = [
            pc_time,
            data.get("ecg", 0),
            data.get("bpm", 0),
            data.get("leadOff", 0),
            data.get("ts", 0)
        ]

        writer.writerow(row)

        # langsung tulis ke disk
        csv_file.flush()

        print(row)

    except Exception as e:
        print("❌ Error:", e)

# ================= MQTT CLIENT =================
client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)

print("🎧 Waiting ECG data... (CTRL+C to stop)")

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\n🛑 Recording stopped")
    csv_file.close()