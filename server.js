const mqtt = require('mqtt');
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

// ================= WEB =================
app.use(express.static('public'));

// ================= MQTT =================
const mqttClient = mqtt.connect('mqtt://10.170.222.19:1883');

mqttClient.on('connect', () => {
  console.log('✅ MQTT connected');

  mqttClient.subscribe([
    'sensor/ppg',
    'sensor/ecg',
    'sensor/emg'   // ⭐ TAMBAHAN
  ]);
});

// ================= MQTT MESSAGE =================
mqttClient.on('message', (topic, message) => {

  try {
    const data = JSON.parse(message.toString());

    switch(topic) {

      case 'sensor/ppg':
        io.emit('ppg', data);
        break;

      case 'sensor/ecg':
        io.emit('ecg', data);
        break;

      case 'sensor/emg':     // ⭐ EMG STREAM
        io.emit('emg', data);
        break;
    }

  } catch (e) {
    console.error("JSON error:", e);
  }
});

// ================= SERVER =================
server.listen(3000, () => {
  console.log('🌐 http://localhost:3000');
});