#include <ESP8266HTTPClient.h>
#include <ESP8266WiFi.h>
#include <SPI.h>
#include "MFRC522.h"

// config

#define RST_PIN  0
#define SS_PIN  15
#define LED 2
#define BUTTON 5

#define CARD_UID_SIZE 4

#define MAX_NFC_SELF_TEST_RETRIES 10
#define MAX_WIFI_CONNECT_WAIT_RETRIES 10
#define MAX_NFC_PROBE_RETRIES 2
#define BUTTON_PRESS_WAIT 80

#define WIFI_SSID "james_dorm_iot"
#define WIFI_PASS "internetofshit"

#define API_BASE_URL "http://ass.woliucloud.cn/v1/"
#define USER_AGENT "ClassroomTerminal 1.0"

// config end

bool wifi_available = false;

int __get_adc_mode(void) { return (int) (ADC_VCC); }

MFRC522 mfrc522(SS_PIN, RST_PIN);

void setup() {
  pinMode(LED, OUTPUT);
  pinMode(BUTTON, INPUT);
  digitalWrite(LED, LOW);

  // Initialize serial
  Serial.begin(115200);
  delay(250);

  // Check system info
  Serial.print(F("Checking chip ID..."));
  Serial.println(ESP.getChipId(), HEX);
  Serial.print(F("Checking input voltage..."));
  Serial.println(ESP.getVcc());

  // Initialize SPI
  Serial.print(F("Init SPI"));
  SPI.begin();
  for (int i = 4; i; --i) {
    Serial.print(F("."));
    delay(25);
  }
  Serial.println(F("OK"));

  // Probe MFRC522 software version
  // 0x91 == version 1.0; 0x92 == version 2.0
  Serial.print(F("Probing MFRC522..."));
  mfrc522.PCD_Init();
  mfrc522.PCD_SetAntennaGain(mfrc522.RxGain_max);
  int mfrc522_version = mfrc522.PCD_ReadRegister(mfrc522.VersionReg);
  if (mfrc522_version != 0x91 && mfrc522_version != 0x92) {
    Serial.print(F("unknown software version "));
    flash_twice();
  } else {
    Serial.print("version ");
  }
  Serial.println(mfrc522_version, HEX);


  // Perform MFRC522 self test
  bool hasFailed = false;
  int retries = 0;
  Serial.print(F("Testing NFC..."));
  while ((!mfrc522.PCD_PerformSelfTest()) && (retries < MAX_NFC_SELF_TEST_RETRIES))
  {
    Serial.print(F("."));
    hasFailed = true;
    ++retries;
    delay(100);
  }
  
  if (hasFailed) {
    Serial.println(F("Failed"));
    // if we are unable to init the module, just flash LED
    while (true) {
      digitalWrite(LED, LOW);
      delay(50);
      digitalWrite(LED, HIGH);
      delay(50);
    }
  } else {
    // after self test we need to init the module again
    Serial.println(F("OK"));
    mfrc522.PCD_Init();
    mfrc522.PCD_SetAntennaGain(mfrc522.RxGain_max);
  }

  // Try to connect to Wi-Fi
  Serial.print(F("Connecting to Wi-Fi..."));
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  retries = 0;
  while ((WiFi.status() != WL_CONNECTED) && (retries++ < MAX_WIFI_CONNECT_WAIT_RETRIES)) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(F("OK"));
    wifi_available = true;
    register_device();
  } else {
    Serial.println(F("Failed"));
  }
  WiFi.printDiag(Serial);

  Serial.println(F("Classroom Terminal ready."));
}

byte last_card_uid[CARD_UID_SIZE] = {0};
bool last_contacted = false;
int button_wait_countdown;

void loop() { 
  // check Wi-Fi
  if (WiFi.status() == WL_CONNECTED) {
    digitalWrite(LED, HIGH);
    if (!wifi_available) {
      // recovering from a disconnection; re-register device
      register_device();
      wifi_available = true;
    }
    delay(50);
  } else {
    last_contacted = false;
    wifi_available = false;
    digitalWrite(LED, LOW);
    Serial.println(F("[WARNING] Wi-Fi disconnected"));
    delay(50);
    return;
  }

   // check button press
   if (digitalRead(BUTTON) == LOW) {
     Serial.println(F("Button pressed, entering card waiting mode"));
     for (button_wait_countdown = BUTTON_PRESS_WAIT; button_wait_countdown; --button_wait_countdown) {
      check_card_routine();
     }
     Serial.println(F("Card waiting mode timed out"));
   }

}

void check_card_routine() {
    // Look for new cards
  int retries = 0;
  bool result = false;
  while ((!(result=mfrc522.PICC_IsNewCardPresent())) && retries++ < MAX_NFC_PROBE_RETRIES) {
    delay(50);
  }
  if (!result) {
    last_contacted = false;
    return;
  }
  
  // Select one of the cards
  if (!mfrc522.PICC_ReadCardSerial()) {
    last_contacted = false;
    Serial.println(F("[WARNING] Unable to select card"));
    delay(50);
    return;
  }
  
  // got card; flash LED
  digitalWrite(LED, LOW);

  // if the card is always detectable between 2 simultaneous probe
  if (last_contacted) {
    // check if it is the same card
    bool is_same = true;
    for (int i = 0; i < CARD_UID_SIZE; ++i) {
      if (last_card_uid[i] != mfrc522.uid.uidByte[i]) {
        is_same = false;
        break;
      }
    }
    // the same card has not been removed, so do not trigger action
    if (is_same) {
      delay(50);
      return;
    }
  }
  
  // a new card has arrived
  last_contacted = true;
  memcpy(last_card_uid, mfrc522.uid.uidByte, CARD_UID_SIZE);
  
  // Show some details of the PICC (that is: the tag/card)
  Serial.print(F("Card UID:"));
  print_byte_array(mfrc522.uid.uidByte, mfrc522.uid.size);
  Serial.println();

  trigger_action();
  
  delay(50);
  digitalWrite(LED, HIGH);
  delay(50);
}

void print_byte_array(byte *buffer, byte bufferSize) {
  for (byte i = 0; i < bufferSize; i++) {
    Serial.printf(" %02X", buffer[i]);
  }
}

void flash_twice() {
  digitalWrite(LED, LOW);
  delay(100);
  digitalWrite(LED, HIGH);
  delay(100);
  digitalWrite(LED, LOW);
  delay(100);
  digitalWrite(LED, HIGH);
  delay(100);
}

void register_device() {
  Serial.print(F("Registering device..."));
  HTTPClient http;

  // get device info
  unsigned char buf[200] = {0};
  sprintf((char*)buf, "chipid=%X&voltage=%d&wifi=%s", ESP.getChipId(), ESP.getVcc(), WIFI_SSID);

  // send HTTP request
  http.begin(API_BASE_URL "device_reg");
  http.setUserAgent(USER_AGENT);
  int httpCode = http.POST(buf, strlen((const char*)buf));
  Serial.print(httpCode);
  if (httpCode > 0){
    Serial.println();
  } else {
    // HTTP error
    Serial.printf(" %s\n", http.errorToString(httpCode).c_str());
    flash_twice();
  }
  http.end();
}

void trigger_action() {
  Serial.print(F("Triggering action..."));
  HTTPClient http;

  // gather information
  unsigned char buf[200] = {0};
  sprintf((char*)buf, "chipid=%X&cardid=", ESP.getChipId());

  int i;
  unsigned char *p;

  for (i = 0, p = buf + strlen((const char*) buf); i < CARD_UID_SIZE; ++i, p+=2) {
    sprintf((char*)p, "%02X", last_card_uid[i]);
  }
  
  // send HTTP request
  http.begin(API_BASE_URL "signout");
  http.setUserAgent(USER_AGENT);
  int httpCode = http.POST(buf, strlen((const char*)buf));
  Serial.print(httpCode);
  if (httpCode > 0){
    Serial.println();
  } else {
    // HTTP error
    Serial.printf(" %s\n", http.errorToString(httpCode).c_str());
    flash_twice();
  }
  http.end();
}

