from flask import Flask, render_template
from pymongo import MongoClient, errors
import pandas as pd
import datetime
import os

app = Flask(__name__)

# --- MongoDB Connection ---
MONGO_URI = "mongodb+srv://iotuser:iotpassword123@cluster0.mismnac.mongodb.net/environment_monitoring?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['environment_monitoring']
collection = db['sensors_datas']

# --- Forecast CSV File ---
basedir = os.path.abspath(os.path.dirname(__file__))
FORECAST_FILE = os.path.join(basedir, 'forecast_data', 'forecast_24hr_resultsnew.csv')

def calibrate_air_quality(raw_value):
    raw_min = 100
    raw_max = 800
    ppm_min = 400
    ppm_max = 2000
    calibrated = ppm_min + ((raw_value - raw_min) / (raw_max - raw_min)) * (ppm_max - ppm_min)
    return round(max(ppm_min, min(calibrated, ppm_max)), 2)

def calibrate_noise_level(raw_value):
    raw_min = 0
    raw_max = 4095
    db_min = 30
    db_max = 120
    calibrated = db_min + ((raw_value - raw_min) / (raw_max - raw_min)) * (db_max - db_min)
    return round(max(db_min, min(calibrated, db_max)), 2)

def detect_anomalies(values, timestamps, window=3, threshold=2.5):
    df = pd.DataFrame({'value': values}, index=pd.to_datetime(timestamps))
    df['rolling_mean'] = df['value'].rolling(window=window, center=True).mean()
    df['rolling_std'] = df['value'].rolling(window=window, center=True).std()
    df['anomaly'] = abs(df['value'] - df['rolling_mean']) > threshold * df['rolling_std']
    return df[df['anomaly']].index.strftime('%H:%M').tolist()

def get_realtime_data():
    try:
        client.admin.command('ping')
        print("[✅] MongoDB connection successful.")
    except errors.ConnectionFailure:
        print("[❌] MongoDB connection failed!")
        return {}

    try:
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
        one_hour_ago = now - datetime.timedelta(hours=1)
        one_hour_ago_str = one_hour_ago.isoformat()

        cursor = collection.find({
            "local_timestamp": {"$gte": one_hour_ago_str}
        }).sort("local_timestamp", 1)

        docs = list(cursor)
        print(f"[DEBUG] Filtered documents (1hr): {len(docs)}")

        buckets = {}
        co2_values = []
        noise_db_values = []

        latest_co2_ppm = 0
        latest_noise_db = 0

        for doc in docs:
            ts_str = doc.get('local_timestamp')
            if ts_str:
                ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                rounded_ts = ts.replace(minute=(ts.minute // 5) * 5, second=0, microsecond=0)
                label = rounded_ts.strftime("%H:%M")
                if label not in buckets:
                    buckets[label] = {"temperature": [], "humidity": [], "air_quality": [], "noise_level": []}

                raw_aq = doc.get("air_quality", 0)
                raw_noise = doc.get("noise_level", 0)
                co2_ppm = calibrate_air_quality(raw_aq)
                noise_db = calibrate_noise_level(raw_noise)

                co2_values.append(co2_ppm)
                noise_db_values.append(noise_db)
                latest_co2_ppm = co2_ppm
                latest_noise_db = noise_db

                buckets[label]["temperature"].append(doc.get("temperature", 0))
                buckets[label]["humidity"].append(doc.get("humidity", 0))
                buckets[label]["air_quality"].append(co2_ppm)
                buckets[label]["noise_level"].append(noise_db)

        timestamps, temperatures, humidities, air_qualities, noise_levels = [], [], [], [], []
        for label in sorted(buckets):
            timestamps.append(label)
            temperatures.append(sum(buckets[label]["temperature"]) / len(buckets[label]["temperature"]))
            humidities.append(sum(buckets[label]["humidity"]) / len(buckets[label]["humidity"]))
            air_qualities.append(sum(buckets[label]["air_quality"]) / len(buckets[label]["air_quality"]))
            noise_levels.append(sum(buckets[label]["noise_level"]) / len(buckets[label]["noise_level"]))

        anomalies = {
            "temperature": detect_anomalies(temperatures, timestamps),
            "humidity": detect_anomalies(humidities, timestamps),
            "air_quality": detect_anomalies(air_qualities, timestamps),
            "noise_level": detect_anomalies(noise_levels, timestamps)
        }

        avg_co2_ppm = round(sum(co2_values) / len(co2_values), 2) if co2_values else 0
        avg_noise_db = round(sum(noise_db_values) / len(noise_db_values), 2) if noise_db_values else 0

        air_quality_alerts = []
        for ts, co2 in zip(timestamps, air_qualities):
            if co2 > 1500:
                air_quality_alerts.append(f"☠️ Hazardous air quality now at {ts} (CO₂ {co2} ppm)")
            elif co2 > 1000:
                air_quality_alerts.append(f"🌫️ Poor air quality now at {ts} (CO₂ {co2} ppm)")

        return {
            "timestamps": timestamps,
            "temperatures": temperatures,
            "humidities": humidities,
            "air_qualities": air_qualities,
            "noise_levels": noise_levels,
            "anomalies": anomalies,
            "co2_metrics": {
                "latest": latest_co2_ppm,
                "average": avg_co2_ppm
            },
            "noise_metrics": {
                "latest": latest_noise_db,
                "average": avg_noise_db
            },
            "air_quality_alerts": air_quality_alerts[:5]
        }

    except Exception as e:
        print(f"[❌] Error while querying: {e}")
        return {}

def get_forecast_data():
    try:
        forecast_df = pd.read_csv(FORECAST_FILE)
        forecast_df['air_quality_ppm'] = forecast_df['air_quality'].apply(calibrate_air_quality)
        forecast_df['noise_level_db'] = forecast_df['noise_level'].apply(calibrate_noise_level)

        forecast_alerts = []
        for _, row in forecast_df.iterrows():
            ts = row['timestamp']
            co2 = row['air_quality_ppm']
            if co2 > 1500:
                forecast_alerts.append(f"☠️ Hazardous air quality forecast at {ts} (CO₂ {co2} ppm)")
            elif co2 > 1000:
                forecast_alerts.append(f"🌫️ Poor air quality forecast at {ts} (CO₂ {co2} ppm)")

        return {
            "timestamps": forecast_df['timestamp'].tolist(),
            "temperatures": forecast_df['temperature'].tolist(),
            "humidities": forecast_df['humidity'].tolist(),
            "air_qualities": forecast_df['air_quality_ppm'].tolist(),
            "noise_levels": forecast_df['noise_level_db'].tolist(),
            "alerts": forecast_alerts[:5]
        }

    except Exception as e:
        print(f"[❌] Forecast CSV load failed: {e}")
        return {}

@app.route('/')
def index():
    realtime_data = get_realtime_data()
    forecast_data = get_forecast_data()
    return render_template('index.html',
                           realtime=realtime_data,
                           forecast=forecast_data)

if __name__ == "__main__":
    app.run(debug=True)
