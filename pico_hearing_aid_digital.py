# pico_hearing_aid_digital.py
# Digital hearing aid with gain control and dynamic range compression
# Uses INMP441 I2S mics and PCM5102A DAC

from machine import Pin, I2S, ADC
import time
import math

print("=== Digital Hearing Aid ===")
print("With Gain & Compression")
print()

# ============ PIN CONFIGURATION ============
# I2S Input from INMP441 microphones
I2S_MIC_SCK = 2
I2S_MIC_WS = 3
I2S_MIC_SD = 4

# I2S Output to PCM5102A DAC
I2S_DAC_SCK = 16
I2S_DAC_WS = 17
I2S_DAC_SD = 18

# Potentiometers (ADC inputs)
POT_GAIN_PIN = 28      # GP28 (pin 34) - Gain control
POT_COMPRESS_PIN = 27  # GP27 (pin 32) - Compression attack/release time

# ============ AUDIO CONFIGURATION ============
SAMPLE_RATE = 16000
INPUT_BUFFER_SIZE = 8192
OUTPUT_BUFFER_SIZE = 8192
CHUNK_SIZE = 512  # Smaller chunks for faster pot response

# ============ COMPRESSION SETTINGS ============
# Threshold (above this level, compression kicks in)
# Value is in raw 24-bit sample magnitude
COMPRESS_THRESHOLD = 500000  # Adjust based on testing

# Compression ratio (e.g., 3.0 means 3:1 compression above threshold)
COMPRESS_RATIO = 3.0

# Attack/release time range (controlled by pot)
MIN_TIME_MS = 5      # Fastest (pot at 0)
MAX_TIME_MS = 200    # Slowest (pot at max)

# Gain range (controlled by pot)
MIN_GAIN = 0.5   # Minimum gain (pot at 0)
MAX_GAIN = 8.0   # Maximum gain (pot at max)

# ============ SETUP ADC FOR POTS ============
pot_gain = ADC(POT_GAIN_PIN)
pot_compress = ADC(POT_COMPRESS_PIN)

# ============ SETUP I2S ============
print("Init I2S input...")
audio_in = I2S(
    0,
    sck=Pin(I2S_MIC_SCK),
    ws=Pin(I2S_MIC_WS),
    sd=Pin(I2S_MIC_SD),
    mode=I2S.RX,
    bits=32,
    format=I2S.STEREO,
    rate=SAMPLE_RATE,
    ibuf=INPUT_BUFFER_SIZE
)

print("Init I2S output...")
audio_out = I2S(
    1,
    sck=Pin(I2S_DAC_SCK),
    ws=Pin(I2S_DAC_WS),
    sd=Pin(I2S_DAC_SD),
    mode=I2S.TX,
    bits=32,
    format=I2S.STEREO,
    rate=SAMPLE_RATE,
    ibuf=OUTPUT_BUFFER_SIZE
)

# ============ BUFFERS ============
audio_buffer = bytearray(CHUNK_SIZE)

# ============ COMPRESSOR STATE ============
# Envelope followers for left and right channels
envelope_left = 0.0
envelope_right = 0.0

# Current settings (updated from pots)
current_gain = 1.0
attack_coeff = 0.1
release_coeff = 0.01

def read_pots():
    """Read potentiometers and update settings."""
    global current_gain, attack_coeff, release_coeff
    
    # Read gain pot (0-65535)
    gain_raw = pot_gain.read_u16()
    gain_normalized = gain_raw / 65535.0  # 0.0 to 1.0
    current_gain = MIN_GAIN + gain_normalized * (MAX_GAIN - MIN_GAIN)
    
    # Read compression speed pot
    compress_raw = pot_compress.read_u16()
    compress_normalized = compress_raw / 65535.0  # 0.0 to 1.0
    
    # Calculate attack/release time in ms
    time_ms = MIN_TIME_MS + compress_normalized * (MAX_TIME_MS - MIN_TIME_MS)
    
    # Convert time to coefficient for exponential smoothing
    # coefficient = 1 - e^(-1 / (time_ms * sample_rate / 1000))
    # Simplified: coefficient ≈ 1.0 / (time_ms * sample_rate / 1000)
    samples_per_time = (time_ms / 1000.0) * SAMPLE_RATE
    if samples_per_time > 0:
        attack_coeff = 1.0 / samples_per_time
        release_coeff = 1.0 / samples_per_time  # Same as attack per user request
    
    return current_gain, time_ms

def compress_sample(sample, envelope, gain):
    """Apply compression to a single sample."""
    global envelope_left, envelope_right
    
    # Get absolute value for envelope detection
    abs_sample = abs(sample)
    
    # Update envelope (peak detector with attack/release)
    if abs_sample > envelope:
        # Attack: fast rise to peak
        envelope = envelope + attack_coeff * (abs_sample - envelope)
    else:
        # Release: slow decay
        envelope = envelope + release_coeff * (abs_sample - envelope)
    
    # Calculate compression gain reduction
    if envelope > COMPRESS_THRESHOLD:
        # How many dB above threshold
        over_threshold = envelope / COMPRESS_THRESHOLD
        # Apply compression ratio
        compressed_ratio = 1.0 + (over_threshold - 1.0) / COMPRESS_RATIO
        comp_gain = COMPRESS_THRESHOLD * compressed_ratio / envelope
    else:
        comp_gain = 1.0
    
    # Apply total gain (user gain * compression gain)
    total_gain = gain * comp_gain
    
    # Apply gain to sample
    output = int(sample * total_gain)
    
    # Soft clipping to prevent harsh distortion
    max_val = 0x7FFFFF  # 24-bit max
    if output > max_val:
        output = max_val
    elif output < -max_val:
        output = -max_val
    
    return output, envelope

# ============ MAIN LOOP ============
print()
print("Sample rate:", SAMPLE_RATE, "Hz")
print("Gain range:", MIN_GAIN, "-", MAX_GAIN)
print("Compression time range:", MIN_TIME_MS, "-", MAX_TIME_MS, "ms")
print()
print("Running... Ctrl+C to stop")
print()

loop_count = 0
POT_READ_INTERVAL = 20  # Read pots every N chunks

try:
    while True:
        # Read audio chunk
        num_read = audio_in.readinto(audio_buffer)
        
        if num_read > 0:
            # Read pots periodically
            loop_count += 1
            if loop_count >= POT_READ_INTERVAL:
                loop_count = 0
                gain, comp_time = read_pots()
            
            # Process samples
            num_frames = num_read // 8  # 8 bytes per stereo frame
            
            for i in range(num_frames):
                idx = i * 8
                
                # Read left sample (32-bit little-endian)
                left = audio_buffer[idx] | (audio_buffer[idx+1] << 8) | \
                       (audio_buffer[idx+2] << 16) | (audio_buffer[idx+3] << 24)
                # Read right sample
                right = audio_buffer[idx+4] | (audio_buffer[idx+5] << 8) | \
                        (audio_buffer[idx+6] << 16) | (audio_buffer[idx+7] << 24)
                
                # Convert to signed
                if left >= 0x80000000:
                    left -= 0x100000000
                if right >= 0x80000000:
                    right -= 0x100000000
                
                # Get 24-bit value (shift out lower 8 bits)
                left_24 = left >> 8
                right_24 = right >> 8
                
                # Apply compression
                left_out, envelope_left = compress_sample(left_24, envelope_left, current_gain)
                right_out, envelope_right = compress_sample(right_24, envelope_right, current_gain)
                
                # Convert back to 32-bit (shift up 8 bits)
                left_32 = left_out << 8
                right_32 = right_out << 8
                
                # Handle negative numbers for output
                if left_32 < 0:
                    left_32 += 0x100000000
                if right_32 < 0:
                    right_32 += 0x100000000
                
                # Write back to buffer
                audio_buffer[idx] = left_32 & 0xFF
                audio_buffer[idx+1] = (left_32 >> 8) & 0xFF
                audio_buffer[idx+2] = (left_32 >> 16) & 0xFF
                audio_buffer[idx+3] = (left_32 >> 24) & 0xFF
                audio_buffer[idx+4] = right_32 & 0xFF
                audio_buffer[idx+5] = (right_32 >> 8) & 0xFF
                audio_buffer[idx+6] = (right_32 >> 16) & 0xFF
                audio_buffer[idx+7] = (right_32 >> 24) & 0xFF
            
            # Write to DAC
            audio_out.write(audio_buffer[:num_read])

except KeyboardInterrupt:
    print()
    print("Stopping...")

finally:
    audio_in.deinit()
    audio_out.deinit()
    print("Stopped.")
