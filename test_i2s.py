# test_i2s.py
# Simple test to verify I2S and DAC are working
# Generates a 440Hz sine wave tone

import machine
from machine import Pin, I2S
import array
import math

print("=== I2S DAC Test ===")
print("This will play a 440Hz tone for 5 seconds")
print()

# I2S pins - must match your wiring
I2S_SCK_PIN = 16   # BCK
I2S_WS_PIN = 17    # LCK  
I2S_SD_PIN = 18    # DIN

SAMPLE_RATE = 16000
TONE_FREQ = 440  # Hz (A4 note)
DURATION_SEC = 5
VOLUME = 10000   # Amplitude (max ~32767)

print(f"BCK -> GP{I2S_SCK_PIN}")
print(f"LCK -> GP{I2S_WS_PIN}")
print(f"DIN -> GP{I2S_SD_PIN}")
print()

# Setup I2S
try:
    audio_out = I2S(
        0,
        sck=Pin(I2S_SCK_PIN),
        ws=Pin(I2S_WS_PIN),
        sd=Pin(I2S_SD_PIN),
        mode=I2S.TX,
        bits=16,
        format=I2S.STEREO,
        rate=SAMPLE_RATE,
        ibuf=2048
    )
    print("I2S initialized OK")
except Exception as e:
    print(f"I2S init FAILED: {e}")
    raise

# Generate one cycle of sine wave
samples_per_cycle = SAMPLE_RATE // TONE_FREQ
sine_wave = array.array('h', [0] * (samples_per_cycle * 2))  # stereo

for i in range(samples_per_cycle):
    sample = int(VOLUME * math.sin(2 * math.pi * i / samples_per_cycle))
    sine_wave[i * 2] = sample      # Left
    sine_wave[i * 2 + 1] = sample  # Right

print(f"Generated {samples_per_cycle} samples per cycle")
print()
print("Playing tone... (you should hear a beep)")

# Play for DURATION_SEC seconds
total_cycles = (SAMPLE_RATE * DURATION_SEC) // samples_per_cycle
for i in range(total_cycles):
    audio_out.write(sine_wave)
    if i % 100 == 0:
        print(".", end="")

print()
print("Done!")
audio_out.deinit()

