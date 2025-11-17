#include <Audio.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <SerialFlash.h>

// GUItool: begin automatically generated code
AudioSynthWaveformSine   sine1;          //xy=61,304
AudioInputI2SQuad        mic;      //xy=67,235
AudioMixer4              mix_r; //xy=243,288
AudioMixer4              mix_l;         //xy=244,202
AudioOutputI2S           out;           //xy=496,242
AudioConnection          patchCord1(sine1, 0, mix_l, 2);
AudioConnection          patchCord2(sine1, 0, mix_r, 2);
AudioConnection          patchCord3(mic, 0, mix_l, 0);
AudioConnection          patchCord4(mic, 1, mix_r, 0);
AudioConnection          patchCord5(mic, 2, mix_l, 1);
AudioConnection          patchCord6(mic, 3, mix_r, 1);
AudioConnection          patchCord7(mix_r, 0, out, 1);
AudioConnection          patchCord8(mix_l, 0, out, 0);
// GUItool: end automatically generated code

// Pin definitions
const int POTENTIOMETER_PIN = 18;    // Analog input pin for potentiometer
const int SET_LEFT = 29;
const int SET_RIGHT = 1;
const int BUTTON_PIN = 19;
const int LED_POWER = 0;

// Default params
float gain = 0.5;
int potVal;

void setup() {
  // Initialize audio library
  AudioMemory(16);
  
  // Initialize Serial Communication
  Serial.begin(9600);

  // Set mics left right out pins
  pinMode(SET_LEFT, OUTPUT);

  // Configure pot pin
  pinMode(POTENTIOMETER_PIN, INPUT);

  // Configure LED pin
  pinMode(LED_POWER, OUTPUT);

  // Configure button pin
  pinMode(BUTTON_PIN, INPUT);

  // Default gain
  mix_l.gain(0, 0.5);
  mix_l.gain(1, 0.5);
  mix_l.gain(2, 0.5);
  mix_r.gain(0, 0.5);
  mix_r.gain(1, 0.5);
  mix_r.gain(2, 0.5);

  // Test sine wave
  sine1.amplitude(0);
  sine1.frequency(500);
}

void loop() {
  // Assign mics left right
  digitalWrite(SET_LEFT, LOW);
  digitalWrite(SET_RIGHT, HIGH);

  // Read pot and assign to gain value
  potVal = analogRead(POTENTIOMETER_PIN);
  //Serial.print("potVal is: ");
  //Serial.println(potVal);
  delay(25);
  gain = map(potVal, 0, 1023, 0, 100) / 100.0;

  // Apply gain
  mix_l.gain(0, gain);
  mix_l.gain(1, gain);
  mix_l.gain(2, gain);
  mix_r.gain(0, gain);
  mix_r.gain(1, gain);
  mix_r.gain(2, gain);

  // LED and sine wave on when button pressed
  if (digitalRead(BUTTON_PIN) == HIGH) {
    digitalWrite(LED_POWER, HIGH);
    sine1.amplitude(0.1);
  }
  else {
    digitalWrite(LED_POWER, LOW);
    sine1.amplitude(0);
  }
}
