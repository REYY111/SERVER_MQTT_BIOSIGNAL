const mqtt = require('mqtt');
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');

const app = express();
const server = http.createServer(app);

const io = new Server(server, {
    cors: { origin: "*" },
    transports: ['websocket']
});

app.use(express.static('public'));

// ================= MQTT =================
const MQTT_URL = 'mqtt://10.170.222.19:1883';

const mqttClient = mqtt.connect(MQTT_URL, {
    clientId: 'NodeJS_Dashboard_' + Math.random().toString(16).substr(2,5),
    reconnectPeriod: 1000,
    connectTimeout: 5000,
});

let messageCount = 0;
let messageBuffer = [];
const BATCH_SIZE = 5;

// =====================================================
// MQTT CONNECT
// =====================================================
mqttClient.on('connect', () => {
    console.log('\x1b[32m%s\x1b[0m',
        `✅ MQTT Connected → ${MQTT_URL}`);

    mqttClient.subscribe('sensor/biosignal');
});

// =====================================================
// MESSAGE HANDLER
// =====================================================
mqttClient.on('message', (topic, message) => {

    try {
        const data = JSON.parse(message.toString());
        messageCount++;

        // ================= SAFE PARSING =================
        const payload = {
            pc_time: Date.now(),

            // ---------- EMG ----------
            emg: {
                raw: Number(data.raw ?? 0),
                clean: Number(data.clean ?? 0),
                env: Number(data.envelope ?? 0),
                ts: Number(data.emg_ts ?? 0)
            },

            // ---------- PPG ----------
            ppg: {
                value: Number(data.ppg ?? 0),
                spo2: Number(data.spo2 ?? 0),
                ts: Number(data.ppg_ts ?? 0)
            },

            // ---------- ECG ----------
       ecg: {
    value: Number(data.ecg ?? 0),   // <-- IMPORTANT
    bpm: Number(data.bpm ?? 0),
    leadOff: Number(data.leadOff ?? 0),
    ts: Number(data.ts ?? 0)        // <-- sesuai ESP32
}
        };

        // ================= TERMINAL MONITOR =================
        console.log(
            `[${messageCount}] ` +
            `EMG:${payload.emg.clean.toFixed(2)} | ` +
            `PPG:${payload.ppg.value} | ` +
            `ECG:${payload.ecg.raw} | ` +
            `BPM:${payload.ecg.bpm}`
        );

        // ================= SOCKET STREAM =================
        messageBuffer.push(payload);

        if (messageBuffer.length >= BATCH_SIZE) {
            io.emit('biosignal_batch', messageBuffer);
            messageBuffer = [];
        }

    } catch (e) {
        console.log('\x1b[31m%s\x1b[0m',
            `⚠️ JSON ERROR: ${e.message}`);

        console.log("RAW:", message.toString());
    }
});

// =====================================================
// ERROR HANDLING
// =====================================================
mqttClient.on('error', err => {
    console.log('\x1b[31m%s\x1b[0m',
        `❌ MQTT ERROR: ${err.message}`);
});

mqttClient.on('offline', () => {
    console.log('\x1b[31m%s\x1b[0m',
        '⚠️ Broker Offline');
});

// =====================================================
const PORT = 3000;

server.listen(PORT, () => {
    console.log('\x1b[36m%s\x1b[0m',
        `🌐 Dashboard → http://localhost:${PORT}`);

    console.log(`📡 Topic: sensor/biosignal`);
});