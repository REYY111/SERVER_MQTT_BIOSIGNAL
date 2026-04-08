import paho.mqtt.client as mqtt
import numpy as np
import json
from scipy.signal import butter, filtfilt, find_peaks

# ================= CONFIG =================

MQTT_BROKER = "10.82.218.19"

TOPIC_SUB = "sensor/ppg"
TOPIC_PUB = "sensor/ppg_processed"

FS = 50   # Sampling Frequency

# ================= BUFFER =================

buffer_red_raw = []
buffer_ir_raw  = []

buffer_red_ac = []
buffer_ir_ac  = []

WINDOW = 200


# ================= FILTER =================

def butter_filter(data):

    if len(data) < 15:
        return data

    low = 0.5 / (FS / 2)
    high = 5 / (FS / 2)

    b, a = butter(3, [low, high], btype='band')

    return filtfilt(b, a, data)


# ================= BPM =================

def compute_bpm(ir_signal):

    if len(ir_signal) < 30:
        return 0

    peaks, _ = find_peaks(
        ir_signal,
        distance = FS * 0.5,
        prominence = np.std(ir_signal) * 0.5
    )

    if len(peaks) < 2:
        return 0

    intervals = np.diff(peaks) / FS

    bpm = 60 / np.mean(intervals)

    return bpm


# ================= SPO2 =================

def compute_spo2(red_raw, ir_raw, red_ac, ir_ac):

    dc_red = np.mean(red_raw)
    dc_ir  = np.mean(ir_raw)

    ac_red = np.std(red_ac)
    ac_ir  = np.std(ir_ac)

    if dc_red == 0 or dc_ir == 0:
        return 0

    R = (ac_red / dc_red) / (ac_ir / dc_ir)

    spo2 = 104 - 17 * R

    spo2 = min(100, max(0, spo2))

    return spo2


# ================= MQTT CALLBACK =================

def on_message(client, userdata, msg):

    global buffer_red_raw
    global buffer_ir_raw
    global buffer_red_ac
    global buffer_ir_ac

    try:

        data = json.loads(msg.payload.decode())

        # ===== DATA DARI ESP32 =====

        red_raw = data["red_raw"]
        ir_raw  = data["ir_raw"]

        red_ac = data["red_filtered"]
        ir_ac  = data["ir_filtered"]

        # ===== BUFFER =====

        buffer_red_raw.append(red_raw)
        buffer_ir_raw.append(ir_raw)

        buffer_red_ac.append(red_ac)
        buffer_ir_ac.append(ir_ac)

        if len(buffer_red_raw) > WINDOW:
            buffer_red_raw.pop(0)
            buffer_ir_raw.pop(0)
            buffer_red_ac.pop(0)
            buffer_ir_ac.pop(0)

        # ===== PROCESS =====

        if len(buffer_red_raw) > 100:

            red_f = butter_filter(buffer_red_ac)
            ir_f  = butter_filter(buffer_ir_ac)

            bpm  = compute_bpm(ir_f)

            spo2 = compute_spo2(
                buffer_red_raw,
                buffer_ir_raw,
                red_f,
                ir_f
            )

            # ===== OUTPUT =====

            output = {

                "red_filtered": round(red_f[-1],2),
                "ir_filtered": round(ir_f[-1],2),

                "bpm": round(bpm,2),
                "spo2": round(spo2,2),

                "ts": data.get("ts",0)
            }

            client.publish(TOPIC_PUB, json.dumps(output))

            print(
                "BPM:", round(bpm,1),
                "| SpO2:", round(spo2,1)
            )

    except Exception as e:

        print("ERROR:", e)


# ================= MQTT SETUP =================

client = mqtt.Client()

client.on_message = on_message

client.connect(MQTT_BROKER, 1883)

client.subscribe(TOPIC_SUB)

print("PPG PROCESSOR RUNNING")
print("SUB:", TOPIC_SUB)
print("PUB:", TOPIC_PUB)

client.loop_forever()