#include <Arduino.h>

#define Bpin 2
#define Spin A5
#define Mpin A7

bool test = false;
unsigned long start = 0;
unsigned long last = 0;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  Serial.println("START");

  pinMode(Bpin, INPUT_PULLUP);
  pinMode(Spin, INPUT);
  pinMode(Mpin, INPUT);
}

void loop() {
  // put your main code here, to run repeatedly:
  int bState = digitalRead(Bpin);
 
  if(bState == LOW){
    delay(50);

    while(bState == LOW){
      bState = digitalRead(Bpin);
    }

    test = !test;

    if(test){
      Serial.println("TESTON");
      start = millis();
    } else{
      Serial.println("TESTOFF");
    }
  }

  if(test){
    unsigned long current = millis();

    if(current - last >= 1){
      last = current;

      unsigned long dt = millis() - start;
      float Sin = analogRead(Spin) / 1023.0 * 5.0 * 250;
      float Min = analogRead(Mpin) / 1023.0 * 5.0;

      Serial.print(dt);
      Serial.print(",");
      Serial.print(Sin);
      Serial.print(",");
      Serial.println(Min);
    }
  }
}
