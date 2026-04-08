import os
import json
import csv
import time
import paho.mqtt.client as mqtt
from queue import Queue
from threading import Thread

# ================= CONFIG =================
BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "sensor/#"   # subscribe semua biosignal

data_queue = Queue(maxsize=5000)

# ================= FILE SETUP =================
script_dir = os.path.dirname(os.path.abspath(__file__))
filename = f"data_biosignal_{int(time.time())}.csv"
path = os.path.join(script_dir, filename)

# ================= CSV WRITER THREAD =================
def file_writer_worker():
    print(f"📁 Writing CSV → {path}")

    with open(path, "w", newline="", buffering=1) as f:
        writer = csv.writer(f)

        writer.writerow([
            "pc_time_ms",
            "emg_raw","emg_clean","emg_env","emg_ts",
            "ppg_red_raw","ppg_ir_raw","ppg_red","ppg_ir","ppg_ts",
            "ecg_raw","ecg_bpm","ecg_leadOff","ecg_ts"
        ])

        while True:
            row = data_queue.get()
            if row is None:
                break

            writer.writerow(row)
            data_queue.task_done()

worker_thread = Thread(target=file_writer_worker, daemon=True)
worker_thread.start()

# ================= MQTT CALLBACK =================
start_time = time.time()
counter = 0

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Connected to MQTT Broker")
        client.subscribe(TOPIC, qos=0)
    else:
        print("❌ Connection failed:", rc)

def on_message(client, userdata, msg):
    global counter

    try:
        data = json.loads(msg.payload.decode())

        pc_now = int((time.time() - start_time) * 1000)

        # ---------- EMG ----------
        emg_raw = data.get("raw", 0)
        emg_clean = data.get("clean", 0.0)
        emg_env = data.get("envelope", 0.0)
        emg_ts = data.get("emg_ts", 0)

        # ---------- PPG ----------
        ppg = data.get("ppg", {})
        ppg_red_raw = ppg.get("red_raw", 0)
        ppg_ir_raw = ppg.get("ir_raw", 0)
        ppg_red = ppg.get("red", 0.0)
        ppg_ir = ppg.get("ir", 0.0)
        ppg_ts = ppg.get("ts", 0)

        # ---------- ECG ----------
        ecg_raw = data.get("ecg", 0)
        ecg_bpm = data.get("bpm", 0)
        ecg_leadOff = data.get("leadOff", 0)
        ecg_ts = data.get("ts", 0)

        row = [
            pc_now,
            emg_raw, emg_clean, emg_env, emg_ts,
            ppg_red_raw, ppg_ir_raw, ppg_red, ppg_ir, ppg_ts,
            ecg_raw, ecg_bpm, ecg_leadOff, ecg_ts
        ]

        if not data_queue.full():
            data_queue.put_nowait(row)
            counter += 1

        if counter % 100 == 0:
            print(
                f"📥 Logged:{counter} | Queue:{data_queue.qsize()}",
                end="\r"
            )

    except Exception as e:
        print("⚠️ Parse Error:", e)
        print("RAW:", msg.payload.decode())

# ================= MQTT CLIENT =================
client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="Ultimate_Collector"
)

client.on_connect = on_connect
client.on_message = on_message

client.max_inflight_messages_set(1000)

# ================= MAIN LOOP =================
try:
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\n🛑 Stopping logger...")

finally:
    client.loop_stop()
    data_queue.put(None)
    worker_thread.join()

    print(f"\n✅ Finished. Total rows: {counter}")