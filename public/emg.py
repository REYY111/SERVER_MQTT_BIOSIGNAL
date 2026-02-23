import json
import csv
import time
import paho.mqtt.client as mqtt

# ================= MQTT =================
BROKER = "10.170.222.19"      # IP broker MQTT
PORT = 1883
TOPIC = "sensor/emg"

# ================= FILE =================
filename = f"emg_record_{int(time.time())}.csv"

csv_file = open(filename, mode="w", newline="")
writer = csv.writer(csv_file)

# header CSV
writer.writerow([
    "pc_time_ms",
    "emg_timestamp",
    "raw_adc",
    "clean_emg",
    "envelope"
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
            data["ts"],
            data["raw"],
            data["clean"],
            data["envelope"]
        ]

        writer.writerow(row)

        # IMPORTANT → langsung tulis disk
        csv_file.flush()

        print(row)

    except Exception as e:
        print("❌ Error:", e)

# ================= MQTT CLIENT =================
client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)

print("🎧 Waiting EMG data... (CTRL+C to stop)")

try:
    client.loop_forever()

except KeyboardInterrupt:
    print("\n🛑 Recording stopped")
    csv_file.close()