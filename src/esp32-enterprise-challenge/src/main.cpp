// including libraries
#include <WiFi.h>
#include <HTTPClient.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <DHT.h>
#include <MPU6050.h>
#include <SD.h>

// configuring WiFi
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// spreadsheet link
const char* spreadsheet = "https://script.google.com/macros/s/AKfycbzDBpGLNFldK01ENAk_Ju5Hb2rvptrOz55I9MNBPGBu5BxYO5PiI-ZNcMkWyPlDp3P9Iw/exec";

// setting client date/time 
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", 0, 60000);

// DHT22 variable definition and configuration
#define DHTPIN 2        
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

// configuring MPU
MPU6050 mpu;
int16_t ax, ay, az, gx, gy, gz;
float ax0, ay0, az0;  // reference starting position

// configuring SD card
#define SD_CS 4   
File myFile;

// parameters
float tempMax = 60.0;  // maximum acceptable part temperature
float limitVibration = 2000; // variation limit to consider strong vibration


// DHT22 reading function
float readTemperature() {
  float t = dht.readTemperature();
  if (isnan(t)) {
    Serial.println("Error reading DHT22");
    return -1000; 
  }
  return t;
}

// MPU6050 reading function
bool readMPU() {
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  // Calculates difference from initial position
  float diffX = abs(ax - ax0);
  float diffY = abs(ay - ay0);
  float diffZ = abs(az - az0);

  if (diffX > limitVibration || diffY > limitVibration || diffZ > limitVibration) {
    return true; // excessive vibration
  }
  return false; // normal
}

// SD save function
void saveData(float temp, bool vibration, String formattedTime) {
  /*DateTime now = rtc.now();*/
  myFile = SD.open("data.csv", FILE_WRITE);

  if (myFile) {
    myFile.print(formattedTime); // date and time
    myFile.print(",");
    myFile.print(temp);
    myFile.print(",");
    myFile.println(vibration ? "HIGH VIBRATION" : "NORMAL");
    myFile.close();
    Serial.println("Data saved on SD!");
  } else {
    Serial.println("Error opening file on SD!");
  }
}

/*
// variable
String formattedTime = timeClient.getFormattedTime();
float temperature = readTemperature();
bool vibrationHigh = readMPU();*/

// ---- Setup ----
void setup() {
  // enable serial monitor
  Serial.begin(115200);

  // initialize WiFi
  WiFi.begin(ssid, password);
  while(WiFi.status() != WL_CONNECTED){
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi Successfully!");  

  // initialize DHT22
  dht.begin();

  // initialize timeClient
  timeClient.begin();
  timeClient.update();

  // initialize MPU6050
  Wire.begin(21,22);
  mpu.initialize();
  if (!mpu.testConnection()) {
    Serial.println("Failed to connect MPU6050");
    while (1);
  }
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
  ax0 = ax; ay0 = ay; az0 = az; // initial reference values

  // initialize SD Card
  if (!SD.begin(SD_CS)) {
    Serial.println("Failed to initialize SD!");
    while (1);
  }

  Serial.println("System ready!");
}

// ---- Loop ----
void loop() {

  if (WiFi.status() == WL_CONNECTED) { 
      HTTPClient http;
      http.begin(spreadsheet);
      http.addHeader("Content-Type", "application/json");
    
  timeClient.update();

  // variable
  String formattedTime = timeClient.getFormattedTime();
  float temperature = readTemperature();
  bool vibrationHigh = readMPU();

  String jsonData = "{";
  jsonData += "\"method\":\"append\",";
  jsonData += "\"timestamp\":\"" + formattedTime + "\",";
  jsonData += "\"temperature\":" + String(temperature) + ",";
  jsonData += "\"vibration\":\"" + String(vibrationHigh ? "HIGH" : "NORMAL") + "\"";
  jsonData += "}";
      
  int httpResponseCode = http.POST(jsonData);

  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println(httpResponseCode);
    Serial.println(response);
  } else {
    Serial.println("Error sending information: " + String(httpResponseCode));
  }

  http.end();
  
  Serial.print("Time: ");
  Serial.print(formattedTime);
  Serial.print(" | Temperature: ");
  Serial.print(temperature);
  Serial.print(" °C | Vibration: ");
  Serial.println(vibrationHigh ? "HIGH" : "NORMAL");

  saveData(temperature, vibrationHigh, formattedTime);
  
  delay(500);

  }else {
    Serial.println("WiFi Disconnected!");
  }

  delay(1000); // reads every 2 seconds
}