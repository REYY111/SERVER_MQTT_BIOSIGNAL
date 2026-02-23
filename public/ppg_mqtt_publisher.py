import pandas as pd
import numpy as np
import time
import json
from scipy.signal import butter, filtfilt
import paho.mqtt.client as mqtt

# ========= MQTT =========
BROKER = "localhost"
PORT = 1883
TOPIC = "sensor/ppg"

client = mqtt.Client()
client.connect(BROKER, PORT, 60)

# ========= BACA CSV =========
data = pd.read_csv("datair.csv")

if 'IR Value' in data.columns:
    ir = data['IR Value']
else:
    ir = data.iloc[:, 2]

ir = pd.to_numeric(ir, errors='coerce').dropna().values

# ========= FILTER =========
fs = 25  # Hz
dc = np.mean(ir)
ac = ir - dc

b, a = butter(3, [0.5/(fs/2), 4/(fs/2)], btype='band')
filtered = filtfilt(b, a, ac)

ppg = dc + (filtered / np.max(np.abs(filtered))) * 50

# ========= STREAM =========
print("📡 Streaming realtime...")

for raw, filt in zip(ir, ppg):
    payload = {
        "raw": float(raw),
        "filtered": float(filt)
    }

    client.publish(TOPIC, json.dumps(payload))
    time.sleep(1/fs)   # ⬅️ INI KUNCI REALTIME

print("✅ Selesai")