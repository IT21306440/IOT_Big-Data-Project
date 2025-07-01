from pymongo import MongoClient
from datetime import datetime

MONGO_URI = "mongodb+srv://iotuser:iotpassword123@cluster0.mismnac.mongodb.net/environment_monitoring?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
collection = client["environment_monitoring"]["sensor_data"]

print("🔁 Converting string-based timestamps to ISODate...")

# Match documents where `timestamp` is a string
docs = collection.find({ "timestamp": { "$type": "string" } })

count = 0
for doc in docs:
    try:
        iso = datetime.fromisoformat(doc["timestamp"].replace("Z", "+00:00"))
        collection.update_one({ "_id": doc["_id"] }, { "$set": { "timestamp": iso } })
        count += 1
    except Exception as e:
        print(f"⚠️ Failed to convert {doc['_id']}: {e}")

print(f"✅ Converted {count} timestamps successfully.")
