#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ArduinoJson.h>

// Wi-Fi Credentials
const char* ssid = "Janindu";
const char* password = "J.udana2000";

// MQTT Broker Credentials
const char* mqttServer = "36225042fed44b109e454fd294b50e37.s1.eu.hivemq.cloud";
const int mqttPort = 8883;
const char* mqttUser = "Janindu";
const char* mqttPassword = "Janindu2000";

// MQTT Topic
const char* topic = "schoolzone/environment";

// Sensor Setup
#define DHTPIN 21
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

#define MQ135_PIN 34
#define SOUND_PIN 35

WiFiClientSecure secureClient;
PubSubClient client(secureClient);

void setupWiFi() {
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 10) {
    delay(1000);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n WiFi Connected.");
    secureClient.setInsecure(); // Only for quick TLS test
  } else {
    Serial.println("\n WiFi Connection Failed! Restarting...");
    ESP.restart();
  }
}

void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT Broker...");
    if (client.connect("ESP32Publisher", mqttUser, mqttPassword)) {
      Serial.println(" Connected to MQTT!");
    } else {
      Serial.print(" MQTT connect failed (rc=");
      Serial.print(client.state());
      Serial.println("). Retrying in 5 seconds...");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  setupWiFi();
  client.setServer(mqttServer, mqttPort);
}

bool validateSensorData(float temp, float hum, int gas, int noise) {
  if (isnan(temp) || temp < -40 || temp > 80) return false;
  if (isnan(hum) || hum < 0 || hum > 100) return false;
  if (gas < 0 || gas > 4095) return false; // ESP32 analog range
  if (noise < 0 || noise > 4095) return false;
  return true;
}

void loop() {
  if (!client.connected()) {
    reconnectMQTT();
  }
  client.loop();

  // Read sensors
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  int airQuality = analogRead(MQ135_PIN);
  int noiseLevel = analogRead(SOUND_PIN);

  // Validate sensor readings
  if (!validateSensorData(temperature, humidity, airQuality, noiseLevel)) {
    Serial.println(" Invalid sensor data detected. Skipping this publish cycle.");
    delay(5000);
    return; // Skip this round
  }

  // Prepare JSON
  StaticJsonDocument<200> doc;
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  doc["air_quality"] = airQuality;
  doc["noise_level"] = noiseLevel;
  doc["zone"] = "playground"; // Example zone name

  char buffer[256];
  size_t n = serializeJson(doc, buffer);

  // Publish to MQTT
  if (client.publish(topic, buffer, n)) {
    Serial.println(" Data Published: ");
    Serial.println(buffer);
  } else {
    Serial.println(" Failed to Publish Data");
  }

  delay(60000); // 1 minute delay
}

