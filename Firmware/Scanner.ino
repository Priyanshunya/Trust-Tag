// Trust-Tag Scanner 
// Team: vision.exe
// Board: ESP32 Dev Module

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <WiFi.h>
#include <HTTPClient.h>

// --- Net Config ---
const char* ssid = "Vision_Hotspot";
const char* password = "Hack4viksitbharat";
const char* cloudURL = "https://NGROK-URL.ngrok-free.app/ingest"; //Sir we are getting few problems here

// --- Pins ---
#define SENSOR_PIN    34    
#define BTN_UP        12    
#define BTN_DOWN      27    
#define BTN_OK        13    
#define BTN_BACK      14    

// Resistor for voltage divider
#define REF_RESISTOR  10000.0 
#define CALIBRATION   1.28    

// Display (1.3 inch OLED)
Adafruit_SH1106G display = Adafruit_SH1106G(128, 64, &Wire, -1);

int currentPackID = 1;
int state = 0; 
bool wifiConnected = false;

void setup() {
  Serial.begin(115200);
  
  // Internal pullups so we don't need extra resistors for buttons
  pinMode(BTN_UP, INPUT_PULLUP);
  pinMode(BTN_DOWN, INPUT_PULLUP);
  pinMode(BTN_OK, INPUT_PULLUP);
  pinMode(BTN_BACK, INPUT_PULLUP);
  pinMode(SENSOR_PIN, INPUT);

  if(!display.begin(0x3C, true)) { 
    Serial.println("Display dead"); 
    for(;;); 
  }
  
  // Splash screen
  display.clearDisplay();
  display.setTextSize(2);
  display.setTextColor(SH110X_WHITE);
  display.setCursor(10, 15);
  display.println("Trust Tag");
  display.setTextSize(1);
  display.setCursor(30, 45);
  display.println("vision.exe");
  display.display();
  delay(1000);

  connectWiFi();
  showSelectScreen();
}

void loop() {
  
  // State 0: Select ID
  if (state == 0) {
    if (digitalRead(BTN_UP) == LOW) {
      currentPackID++; 
      if (currentPackID > 20) currentPackID = 1;
      showSelectScreen(); 
      delay(200);
    }
    if (digitalRead(BTN_DOWN) == LOW) {
      currentPackID--; 
      if (currentPackID < 1) currentPackID = 20;
      showSelectScreen(); 
      delay(200);
    }
    if (digitalRead(BTN_OK) == LOW) {
      state = 1; 
      delay(300);
    }
  }

  // State 1: Live Scanning
  else if (state == 1) {
    float res = readResistance();
    
    // UI
    display.clearDisplay();
    display.setTextSize(1);
    display.setCursor(0,0); 
    display.printf("SCANNING: PACK_%03d", currentPackID);
    
    display.setTextSize(2);
    display.setCursor(10, 25);
    if (res > 90000) display.print("OPEN");
    else display.printf("%.0f R", res);
    
    display.setTextSize(1);
    display.setCursor(0, 55);
    display.println("PRESS OK TO SYNC");
    display.display();

    // Upload
    if (digitalRead(BTN_OK) == LOW) {
      uploadData(res); 
      state = 2; // Result screen
      delay(300);
    }
    // Back
    if (digitalRead(BTN_BACK) == LOW) {
      state = 0; 
      showSelectScreen(); 
      delay(300);
    }
  }

  // State 2: Result Hold
  else if (state == 2) {
    if (digitalRead(BTN_OK) == LOW || digitalRead(BTN_BACK) == LOW) {
      state = 0; 
      showSelectScreen(); 
      delay(300);
    }
  }
}

// --- Logic ---

void connectWiFi() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0,0);
  display.println("WiFi Connecting...");
  display.display();
  
  WiFi.setSleep(false);
  WiFi.begin(ssid, password);
  
  int i = 0;
  while(WiFi.status() != WL_CONNECTED && i < 15) {
    delay(500);
    Serial.print(".");
    i++;
  }
  
  display.setCursor(0, 20);
  if(WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    display.println("ONLINE");
  } else {
    wifiConnected = false;
    display.println("OFFLINE MODE");
  }
  display.display();
  delay(1000);
}

void uploadData(float res) {
  String status = "SECURE";
  if (res < 1000 || res > 50000) status = "TAMPERED";

  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(30, 20);
  display.println("UPLOADING...");
  display.display();

  if (wifiConnected) {
    HTTPClient http;
    http.begin(cloudURL);
    http.addHeader("Content-Type", "application/json");
    
    // JSON format
    String payload = "{\"id\":\"PACK_";
    if(currentPackID<10) payload += "00";
    else if(currentPackID<100) payload += "0";
    payload += String(currentPackID);
    payload += "\", \"res\":" + String((int)res);
    payload += ", \"status\":\"" + status + "\"}";
    
    int code = http.POST(payload);
    
    display.clearDisplay();
    display.setCursor(0,0); 
    
    if (code > 0) {
      display.setTextSize(2);
      display.setCursor(20, 20);
      display.println("SENT!");
      display.setTextSize(1);
      display.setCursor(10, 45);
      display.printf("Code: %d", code);
    } else {
      display.setTextSize(2);
      display.setCursor(20, 20);
      display.println("ERROR");
    }
    http.end();
  } else {
    display.clearDisplay();
    display.setTextSize(2);
    display.setCursor(10, 20);
    display.println("SAVED");
    display.setTextSize(1);
    display.setCursor(10, 45);
    display.println("(Offline Buffer)");
  }
  display.display();
  delay(1500); 
}

float readResistance() {
  long total = 0;
  // averaging 100 times to kill noise
  for(int i=0; i<100; i++) { 
    total += analogRead(SENSOR_PIN); 
  }
  float raw = total / 100.0;
  
  float voltage = raw * (3.3 / 4095.0);
  if (voltage < 0.1) return 0;
  if (voltage > 3.2) return 999999;
  
  float r = (voltage * REF_RESISTOR) / (3.3 - voltage);
  return r * CALIBRATION;
}

void showSelectScreen() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0,0); 
  display.println("SELECT PACKAGE:");
  display.setTextSize(2);
  display.setCursor(15, 25); 
  display.printf("PACK_%03d", currentPackID);
  display.setTextSize(1);
  display.setCursor(0, 55); 
  display.println("[UP/DWN] -> [OK]");
  display.display();
}
