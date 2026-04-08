import paho.mqtt.client as mqtt
import numpy as np
import json

# ================= CONFIG =================

MQTT_BROKER = "10.82.218.19"

TOPIC_SUB = "sensor/emg"
TOPIC_PUB = "sensor/emg_processed"

FS = 500
WINDOW = 200


# ================= BUFFER =================

buffer_clean = []


# ================= RMS =================

def compute_rms(signal):

    if len(signal) == 0:
        return 0

    signal = np.array(signal)

    rms = np.sqrt(np.mean(signal**2))

    return rms


# ================= MQTT CALLBACK =================

def on_message(client, userdata, msg):

    global buffer_clean

    try:

        data = json.loads(msg.payload.decode())

        raw   = data["raw"]
        clean = data["clean"]

        buffer_clean.append(clean)

        if len(buffer_clean) > WINDOW:
            buffer_clean.pop(0)

        # ===== RMS =====

        rms = compute_rms(buffer_clean)

        # ===== OUTPUT =====

        output = {

            "raw_emg": raw,
            "clean_emg": round(clean,2),
            "rms_emg": round(rms,3),

            "ts": data.get("ts",0)

        }

        client.publish(TOPIC_PUB, json.dumps(output))

        print(
            "RAW:", raw,
            "| CLEAN:", round(clean,2),
            "| RMS:", round(rms,3)
        )

    except Exception as e:

        print("ERROR:", e)


# ================= MQTT SETUP =================

client = mqtt.Client()

client.on_message = on_message

client.connect(MQTT_BROKER, 1883)

client.subscribe(TOPIC_SUB)

print("EMG PROCESSOR RUNNING")
print("SUB:", TOPIC_SUB)
print("PUB:", TOPIC_PUB)

client.loop_forever()