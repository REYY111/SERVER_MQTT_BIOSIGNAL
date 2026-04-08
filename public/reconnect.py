import os, json, csv, time
import paho.mqtt.client as mqtt

BROKER = "10.170.222.19"
PORT = 1883
TOPIC = "sensor/biosignal"

script_dir = os.path.dirname(os.path.abspath(__file__))
filename = f"biosignal_{int(time.time())}.csv"
file_path = os.path.join(script_dir, filename)

csv_file = open(file_path, "w", newline="")
writer = csv.writer(csv_file)
writer.writerow(["pc_time_ms", "emg_raw", "emg_clean", "emg_envelope", "emg_ts", "ppg_red_raw", "ppg_ir_raw", "ppg_red", "ppg_ir", "ppg_ts"])
csv_file.flush()

start_time = time.time()
counter = 0

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Terhubung! Menunggu data...")
        client.subscribe(TOPIC, qos=0) # Pakai QoS 0 biar gak numpuk antrian
    else:
        print(f"❌ Gagal: {rc}")

def on_message(client, userdata, msg):
    global counter
    try:
        data = json.loads(msg.payload.decode())
        pc_time = int((time.time() - start_time) * 1000)
        ppg = data.get("ppg", {})
        
        writer.writerow([
            pc_time, data.get("raw",0), data.get("clean",0.0), data.get("envelope",0.0), data.get("emg_ts",0),
            ppg.get("red_raw",0), ppg.get("ir_raw",0), ppg.get("red",0.0), ppg.get("ir",0.0), ppg.get("ppg_ts",0)
        ])
        
        counter += 1
        if counter % 20 == 0:
            csv_file.flush()
            # Cukup print satu titik aja biar terminal gak berat
            print(".", end="", flush=True) 
            if counter % 1000 == 0: print(f" Total: {counter}")
            
    except:
        pass

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
# Fitur Reconnect Otomatis
client.connect_async(BROKER, PORT, keepalive=60)

try:
    print(f"🚀 Memulai Recording ke {filename}...")
    client.loop_forever() # Fokus total nerima data
except KeyboardInterrupt:
    print("\n🛑 Stop.")
finally:
    csv_file.flush()
    csv_file.close()
    print(f"✅ Selesai. Total data: {counter}")