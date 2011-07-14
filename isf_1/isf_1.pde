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

//
//arduino 2 - servo 2
//arduino 3 - servo 1
//arduino 4 - servo 4
//arduino 5 - servo 3
//arduino 6 - servo 6
//arduino 7 - servo 5
//arduino 8 - bomba 2
//arduino 9 - bomba 1
//arduino 10 - bomba 4
//arduino 11 - bomba 3
//arduino 12 - bomba 6
//arduino 13 - bomba 5

//servos pares 0, 2, 4 - de 90 a 0 (90 baixo -> 0 alto)
//servos impares 1,3,5 - de  0 a 90 (0 baixo, 90 alto)

#include <Servo.h>


String serialData;
Servo myservo[6];

void setup() {

  for (int i=2;i<14;i++)
    pinMode (i, OUTPUT);

  attachAll();

  Serial.begin(9600);
}

void loop () {
  boolean state;
  char angle_char[4],pin_char[3], read_char;    
  int pin, angle;

  serialData = "";

  if (Serial.available()) {
    read_char = Serial.read();
    //Serial.println(read_char);
    if (read_char == 85) { // "U"  char 85
      Serial.print("A");
    } else {
      while(read_char != '\n') {
        delay(5);
        serialData += read_char;
        read_char = Serial.read();
      }
    }
    //Serial.println(serialData);

  }

  if (serialData.startsWith("d")) {
    serialData.substring(1,3).toCharArray(pin_char,3);
    pin = getPumpPin(atoi(pin_char));

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

    if (serialData.substring(3,8).startsWith("d")) {
      detachAll();
    } else if (serialData.substring(3,8).startsWith("a")) {
      attachAll();
    } else {

      serialData.substring(3,8).toCharArray(angle_char,5);
      angle = atoi(angle_char);
      //Serial.println(angle);
      
      if (pin % 2 == 0) 
          angle = 90 - angle;
  
      myservo[pin].write(angle);
      //goSlow (pin, angle, 1, 30);
    }
  }
}

int getPumpPin(int pump) {
  switch (pump) {
    case 0:
      return 9;
    case 1:
      return 8;
    case 2:
      return 11;
    case 3:
      return 10;
    case 4:
      return 13;
    case 5:
      return 12;
  }
}

void goSlow (int pin, int angle, int delta, int interval) {
  
  if (myservo[pin].read() > angle) {
    while (myservo[pin].read()-delta > angle) {
      myservo[pin].write(myservo[pin].read()-delta);
      delay(interval);
    } 
  } else {
      while (myservo[pin].read()+delta < angle) {
        myservo[pin].write(myservo[pin].read()+delta);
        delay(interval);
    } 
  }

}

void attachAll() {
  myservo[0].attach(3, 620,2350);
  myservo[1].attach(2, 620,2350);
  myservo[2].attach(5, 620,2350);
  myservo[3].attach(4, 620,2350);
  myservo[4].attach(7, 620,2350);
  myservo[5].attach(6, 620,2350);  
  for (int i=0; i<6; i++) {
    myservo[i].write(0);
  }
}

void detachAll() {
  for (int i=0; i<6; i++) {
    myservo[i].detach();
  }
}
