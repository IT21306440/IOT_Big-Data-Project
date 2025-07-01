#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Wi-Fi Credentials
const char* ssid = "Janindu";
const char* password = "J.udana2000";

// MQTT Credentials
const char* mqttServer = "36225042fed44b109e454fd294b50e37.s1.eu.hivemq.cloud";
const int mqttPort = 8883;
const char* mqttUser = "Janindu";
const char* mqttPassword = "Janindu2000";

// GPIO Pins
#define RED_LED 26        // Air Quality
#define YELLOW_LED 27     // Noise Level
#define GREEN_LED 25      // Temperature

WiFiClientSecure secureClient;
PubSubClient client(secureClient);

// Blinking control
unsigned long previousMillis = 0;
const long blinkInterval = 500;  // 500 ms
bool redBlink = false;
bool yellowBlink = false;
bool greenBlink = false;

void setupWiFi() {
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n WiFi Connected!");
  secureClient.setInsecure();
}

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.println(" MQTT Message Received:");

  String message;
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);

  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, message);
  if (error) {
    Serial.print(" Failed to parse JSON: ");
    Serial.println(error.c_str());
    return;
  }

  float temperature = doc["temperature"];
  int air_quality = doc["air_quality"];
  int noise = doc["noise_level"];

  Serial.print(" Temp: "); Serial.println(temperature);
  Serial.print(" AirQ: "); Serial.println(air_quality);
  Serial.print(" Noise: "); Serial.println(noise);

  // Air Quality LED Logic
  if (air_quality > 250) {
    redBlink = false;
    digitalWrite(RED_LED, HIGH);
  } else if (air_quality > 100) {
    redBlink = true;
  } else {
    redBlink = false;
    digitalWrite(RED_LED, LOW);
  }

  // Noise Level LED Logic
  if (noise > 100) {
    yellowBlink = false;
    digitalWrite(YELLOW_LED, HIGH);
  } else if (noise > 60) {
    yellowBlink = true;
  } else {
    yellowBlink = false;
    digitalWrite(YELLOW_LED, LOW);
  }

  // Temperature LED Logic
  if (temperature > 32.5) {
    greenBlink = false;
    digitalWrite(GREEN_LED, HIGH);
  } else if (temperature > 30) {
    greenBlink = true;
  } else {
    greenBlink = false;
    digitalWrite(GREEN_LED, LOW);
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT...");
    if (client.connect("ESP32Subscriber", mqttUser, mqttPassword)) {
      Serial.println("connected!");
      client.subscribe("schoolzone/environment");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(". Retrying in 2 seconds...");
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(RED_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);

  setupWiFi();
  client.setServer(mqttServer, mqttPort);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= blinkInterval) {
    previousMillis = currentMillis;

    // Blink only if flagged
    if (redBlink) {
      digitalWrite(RED_LED, !digitalRead(RED_LED));
    }
    if (yellowBlink) {
      digitalWrite(YELLOW_LED, !digitalRead(YELLOW_LED));
    }
    if (greenBlink) {
      digitalWrite(GREEN_LED, !digitalRead(GREEN_LED));
    }
  }
}
