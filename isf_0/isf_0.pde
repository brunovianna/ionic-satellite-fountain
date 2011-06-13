// fountain control
// outputs 2-7 control the servos
// outputs 8-13 control the pump switches
// pump 1 -- pin 2 (servo), pin 8 (switch) -- and son on

// serial protocol
// first char d (for digital), 2nd and 3rd chars the pin (ex 10), 4th char state (1 or 0)
// or
// first char s (for servo), 2nd and 3rd chars the pin (ex 03), 4th, 5th, 6th the angle (ex 070)
//
// examples:
// d051 - turn on nozzle 5 (on pin 13)
// s03080 - turn servo 3 (on pin 10) to 80 degress

#include <Servo.h>


String serialData;
Servo myservo[6];

void setup() {

  for (int i=2;i<14;i++)
    pinMode (i, OUTPUT);

  for (int i=0;i<6;i++)
    myservo[i].attach(i+2);

  Serial.begin(57600);
}

void loop () {
  boolean state;
  char angle_char[4],pin_char[3], read_char;    
  int pin, angle;

  serialData = "";

  if (Serial.available()) {
    read_char = Serial.read();
    Serial.println(read_char);
    while(read_char != '\n') {
      delay(5);
      serialData += read_char;
      read_char = Serial.read();
    }
    Serial.println(serialData);

  }

  if (serialData.startsWith("d")) {
    serialData.substring(1,3).toCharArray(pin_char,3);
    pin = atoi(pin_char) + 8;

    if (serialData.charAt(3) == '0')
      state = LOW;
    else 
      state = HIGH;

    digitalWrite (pin, state);
  } 
  if (serialData.startsWith("s")) {
    
    serialData.substring(1,3).toCharArray(pin_char,3);
    pin = atoi(pin_char);
    //Serial.println(pin);

    serialData.substring(4,8).toCharArray(angle_char,5);
    angle = atoi(angle_char);
    //Serial.println(angle);

    myservo[pin].write(angle);
    
  }
}


