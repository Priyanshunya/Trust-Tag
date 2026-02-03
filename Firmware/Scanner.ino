#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h> 
#include <WiFi.h>
#include <HTTPClient.h>

// --- DISPLAY ---
Adafruit_SH1106G display = Adafruit_SH1106G(128, 64, &Wire, -1);

// --- PINS ---
#define SENSOR_PIN 34
#define BTN_UP 12
#define BTN_DOWN 27
#define BTN_OK 13
#define BTN_BACK 14

// --- PHYSICS & CALIBRATION ---
float ref_resistor = 10000.0; // 10k Ohm Reference
const char* ssid = "Trusttag"; 
const char* password = "Safelogistics";

// --- CLOUD CONFIGURATION ---
const char* cloudURL = "https://ingest-telemetry-697288371886.asia-south1.run.app"; 

// --- STATE VARIABLES ---
int currentPackID = 1;
int state = 0; // 0=Select, 1=Scan, 2=Result
bool wifiConnected = false;

void setup() {
  Serial.begin(115200);
  
  pinMode(BTN_UP, INPUT_PULLUP);
  pinMode(BTN_DOWN, INPUT_PULLUP);
  pinMode(BTN_OK, INPUT_PULLUP);
  pinMode(BTN_BACK, INPUT_PULLUP);
  pinMode(SENSOR_PIN, INPUT);

  if(!display.begin(0x3C, true)) { 
    Serial.println("Display failed"); for(;;); 
  }
  
  display.clearDisplay();
  display.setTextSize(2);
  display.setTextColor(SH110X_WHITE);
  display.setCursor(10, 15);
  display.println("Trust Tag");
  display.setTextSize(1);
  display.setCursor(20, 40);
  display.println("READY TO SCAN");
  display.display();
  delay(1000);

  connectWiFi();
  showSelect();
}

void loop() {
  // STATE 0: SELECT ID
  if (state == 0) {
    if (digitalRead(BTN_UP) == LOW) {
      currentPackID++; if(currentPackID > 20) currentPackID=1;
      showSelect(); delay(200);
    }
    if (digitalRead(BTN_DOWN) == LOW) {
      currentPackID--; if(currentPackID < 1) currentPackID=20;
      showSelect(); delay(200);
    }
    if (digitalRead(BTN_OK) == LOW) {
      state = 1; delay(300); 
    }
  }

  // STATE 1: SCANNING
  else if (state == 1) {
    float res = getResistance();
    showScan(res);
    
    if (digitalRead(BTN_OK) == LOW) {
      upload(res); 
      state = 2; 
      delay(300);
    }
    if (digitalRead(BTN_BACK) == LOW) {
      state = 0; showSelect(); delay(300);
    }
  }

  // STATE 2: RESULT VIEW
  else if (state == 2) {
    if (digitalRead(BTN_OK) == LOW || digitalRead(BTN_BACK) == LOW) {
      state = 0; showSelect(); delay(300);
    }
  }
}

// --- CORE LOGIC ---

float getResistance() {
  long total = 0;
  for(int i=0; i<50; i++) total += analogRead(SENSOR_PIN);
  float v = (total/50.0) * (3.3 / 4095.0);
  
  // Resistance Calculation (Voltage Divider)
  if (v < 0.1) return 99999.0; // Open Circuit
  return ref_resistor * (3.3 - v) / v;
}

void upload(float res) {
  display.clearDisplay(); 
  display.setCursor(30, 25); 
  display.print("SYNCING..."); 
  display.display();

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(cloudURL);
    http.addHeader("Content-Type", "application/json");
    
    // Construct the payload
    String payload = "{\"id\":\"PACK_" + String(currentPackID < 10 ? "00" : (currentPackID < 100 ? "0" : "")) + String(currentPackID) + "\", \"res\":" + String((int)res) + "}";
    
    int code = http.POST(payload);
    String resp = http.getString();
    http.end();
    
    display.clearDisplay(); 
    display.setCursor(10, 20);
    display.setTextSize(2);
    
    if (code == 200) {
       // Check status keywords returned by Section 1
       if(resp.indexOf("REGISTERED") >= 0) {
          display.print("REGISTERED");
       } else if(resp.indexOf("TAMPERED") >= 0) {
          display.setCursor(10, 20);
          display.print("TAMPERED!"); // Critical Alert
       } else {
          display.print("SECURE");
       }
    } else {
       display.setTextSize(1);
       display.printf("ERR CODE: %d", code);
    }
  } else { 
    display.print("OFFLINE"); 
  }
  display.display(); 
  delay(2000);
}

void connectWiFi() {
  WiFi.begin(ssid, password);
  int retry = 0;
  while(WiFi.status() != WL_CONNECTED && retry < 20) {
    delay(500);
    retry++;
  }
  showSelect();
}

void showSelect() {
  display.clearDisplay(); 
  display.setTextSize(1);
  display.setCursor(0,0); 
  display.print("SELECT PKG ID:");
  display.setTextSize(2);
  display.setCursor(20, 30); 
  display.printf("PACK_%03d", currentPackID);
  display.display();
}

void showScan(float r) {
  display.clearDisplay(); 
  display.setTextSize(1);
  display.setCursor(0,0); 
  display.printf("ID: PACK_%03d", currentPackID);
  display.setTextSize(2);
  display.setCursor(20, 30); 
  if(r > 60000) display.print("OPEN"); 
  else display.printf("%.0f R", r);
  display.display();
}
