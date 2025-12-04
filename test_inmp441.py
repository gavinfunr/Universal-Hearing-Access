# test_inmp441.py
# Test INMP441 microphones with visual level meter

from machine import Pin, I2S
import time

print("=== INMP441 Microphone Test ===")
print()

# I2S Input pins
I2S_MIC_SCK = 2
I2S_MIC_WS = 3
I2S_MIC_SD = 4 

SAMPLE_RATE = 16000

print("Initializing I2S...")
audio_in = I2S(
    0,
    sck=Pin(I2S_MIC_SCK),
    ws=Pin(I2S_MIC_WS),
    sd=Pin(I2S_MIC_SD),
    mode=I2S.RX,
    bits=32,
    format=I2S.STEREO,
    rate=SAMPLE_RATE,
    ibuf=4096
)
print("OK!")
print()

buffer = bytearray(256)

# DC offset tracking
dc_left = 0
dc_right = 0

print("Speak into the mics - bars should move!")
print("Left mic (L/R->GND) | Right mic (L/R->3V3)")
print("-" * 55)

try:
    while True:
        num_read = audio_in.readinto(buffer)
        
        if num_read >= 8:
            # Parse first sample
            left_32 = buffer[0] | (buffer[1] << 8) | (buffer[2] << 16) | (buffer[3] << 24)
            right_32 = buffer[4] | (buffer[5] << 8) | (buffer[6] << 16) | (buffer[7] << 24)
            
            # Convert to signed
            if left_32 >= 0x80000000:
                left_32 -= 0x100000000
            if right_32 >= 0x80000000:
                right_32 -= 0x100000000
            
            # Get 24-bit value
            left_24 = left_32 >> 8
            right_24 = right_32 >> 8
            
            # Track DC offset
            dc_left = dc_left * 0.99 + left_24 * 0.01
            dc_right = dc_right * 0.99 + right_24 * 0.01
            
            # Remove DC and get 16-bit value
            left_16 = (left_24 - int(dc_left)) >> 8
            right_16 = (right_24 - int(dc_right)) >> 8
            
            # Level meter (0-20 characters)
            left_level = min(20, abs(left_16) // 500)
            right_level = min(20, abs(right_16) // 500)
            
            left_bar = "#" * left_level + " " * (20 - left_level)
            right_bar = "#" * right_level + " " * (20 - right_level)
            
            print("L:{:7d} [{}] | R:{:7d} [{}]".format(left_16, left_bar, right_16, right_bar))
        
        time.sleep_ms(100)

except KeyboardInterrupt:
    print()
    print("Stopped.")
    audio_in.deinit()
