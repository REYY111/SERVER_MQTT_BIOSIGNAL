import serial
import csv
import time

# Sesuaikan dengan Port ESP32 kamu (cek di Device Manager / Arduino IDE)
PORT = 'COM12' 
BAUD = 115200
filename = f"ppg_serial_{int(time.time())}.csv"

try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print(f"✅ Terhubung ke {PORT}")
    
    with open(filename, mode="w", newline="") as f:
        writer = csv.writer(f)
        # Tulis Header yang sama dengan kodingan analisis kita
        writer.writerow(["red_raw", "red_final (Filtered)", "ir_raw", "ir_final (Filtered)"])
        
        count = 0
        print(f"📁 Recording to: {filename}")
        
        while True:
            line = ser.readline().decode('utf-8').strip()
            if line:
                data = line.split(',')
                if len(data) == 4:
                    writer.writerow(data)
                    count += 1
                    if count % 10 == 0:
                        print(f"🚀 Baris Terkumpul: {count}", end='\r')

except KeyboardInterrupt:
    print(f"\n🛑 Berhenti manual. Total data: {count}")
except Exception as e:
    print(f"❌ Error: {e}")