const mqtt = require('mqtt');
const express = require('express');
const http = require('http');
const path = require('path');
const { Server } = require('socket.io');

const app = express();
const server = http.createServer(app);

// Inisialisasi Socket.io dengan pengiriman instan
const io = new Server(server, {
    cors: { origin: "*" },
    transports: ['websocket'] // Zero delay menggunakan Websocket
});

app.use(express.static(__dirname));
app.get('/', (req, res) => { 
    res.sendFile(path.join(__dirname, 'index.html')); 
});

const MQTT_URL = 'mqtt://192.168.0.102:1883';
const mqttClient = mqtt.connect(MQTT_URL);

mqttClient.on('connect', () => {
    console.log('✅ Connected to MQTT Broker');
    // Subscribe ke kedua topik sekaligus
    mqttClient.subscribe(['sensor/emg_processed', 'sensor/ppg_processed'], (err) => {
        if (!err) {
            console.log('📡 Subscribed to EMG & PPG topics');
        } else {
            console.log('❌ Subscribe Error:', err);
        }
    });
});

// Logic utama penerimaan data
mqttClient.on('message', (topic, message) => {
    try {
        const data = JSON.parse(message.toString());
        
        let payload = {
            topic: topic,
            pc_time: Date.now(),
            data: data
        };

        // Kirim snapshot data ke Frontend via Socket.io
        io.emit('biosignal_data', payload); 

        // Log Terminal untuk Monitoring
        if (topic === 'sensor/ppg_processed') {
            console.log(`[PPG] 💓 BPM: ${data.bpm} | 🩸 SpO2: ${data.spo2}%`);
        } 
        else if (topic === 'sensor/emg_processed') {
            console.log(`[EMG] 💪 RMS: ${data.rms_emg} | Clean: ${data.clean_emg}`);
        }

    } catch (e) {
        console.log(`❌ JSON Parse Error: ${e.message} | Topic: ${topic}`);
    }
});

// Jalankan server di port 3000
server.listen(3000, '0.0.0.0', () => {
    console.log(`🌐 Dashboard Active: http://localhost:3000`);
    console.log(`🚀 Menunggu data dari Python script...`);
});