import json
import requests
import paho.mqtt.client as mqtt
import pandas as pd
import time

# MQTT Settings
MQTT_BROKER = "36225042fed44b109e454fd294b50e37.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_TOPIC = "schoolzone/environment"
MQTT_USER = "Janindu"
MQTT_PASSWORD = "Janindu2000"

# Telegram Settings
BOT_TOKEN = "7369165758:AAGDiHWqzVXnwnXCWFOx7O9r93YSWXzlJPg"
CHAT_ID = "1143061567"

# Thresholds (using calibrated noise dB)
THRESHOLDS = {
    'temperature': 32.5,
    'humidity': 85.0,
    'air_quality': 300,
    'noise_level': 70  
}

# Flood prevention
last_alert_time = 0
ALERT_INTERVAL = 10 * 60  # 10 minutes

# Load historical anomalies
try:
    historical_anomalies = pd.read_csv("C://anomaly detection details//detected_anomalies.csv")
    print("✅ Loaded historical anomalies.")
except Exception as e:
    print(f"⚠️ Failed to load anomaly file: {e}")
    historical_anomalies = pd.DataFrame()

def calibrate_noise_level(raw_value):
    # Example calibration: map raw 0–1023 → 30–120 dB (adjust as needed)
    raw_min, raw_max = 0, 1023
    db_min, db_max = 30, 120
    calibrated = db_min + ((raw_value - raw_min) / (raw_max - raw_min)) * (db_max - db_min)
    return round(calibrated, 2)

def check_historical_pattern(sensor):
    if historical_anomalies.empty:
        return False
    recent = historical_anomalies[historical_anomalies[sensor + "_anomaly"] == True]
    return not recent.empty

def send_combined_telegram_alert(alerts):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    message = "<b>🚨 School Zone Environmental Alerts 🚨</b>\n\n"

    sensor_icons = {
        'temperature': '🌡️',
        'humidity': '💧',
        'air_quality': '🌫️',
        'noise_level': '🔊'
    }

    repeated_pattern_detected = False

    for alert in alerts:
        sensor, value, threshold, historical_flag = alert
        icon = sensor_icons.get(sensor, '🚨')
        message += (
            f"{icon} <b>{sensor.replace('_', ' ').title()} Alert!</b>\n"
            f"📊 Current: <code>{value}</code> | ⚠️ Limit: <code>{threshold}</code>\n"
        )
        if historical_flag:
            message += "🔁 This pattern has occurred before!\n"
            repeated_pattern_detected = True
        message += "\n"

    if repeated_pattern_detected:
        message += "🕒 Real-time anomaly detected. Please check the system\n"

    message += "🕒 Please notify a teacher or system admin."

    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("✅ Combined alert sent!")
    else:
        print(f"❌ Failed to send alert: {response.text}")

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code " + str(rc))
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global last_alert_time
    try:
        data = json.loads(msg.payload.decode())
        print(f"📦 Received data: {data}")

        current_time = time.time()
        alerts_to_send = []

        for sensor, value in data.items():
            if sensor == 'noise_level':
                value = calibrate_noise_level(float(value))  # calibrate noise before checking
                print(f"🔊 Calibrated Noise Level: {value} dB")
            if sensor in THRESHOLDS and float(value) > THRESHOLDS[sensor]:
                historical_flag = check_historical_pattern(sensor)
                alerts_to_send.append((sensor, value, THRESHOLDS[sensor], historical_flag))

        if alerts_to_send:
            if current_time - last_alert_time >= ALERT_INTERVAL:
                send_combined_telegram_alert(alerts_to_send)
                last_alert_time = current_time
            else:
                print("⏳ Skipping combined alert (sent recently)")

    except Exception as e:
        print(f"❌ Error processing message: {e}")

# MQTT Client Setup
client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
client.tls_set()

client.on_connect = on_connect
client.on_message = on_message

print("🔌 Connecting to MQTT...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()
