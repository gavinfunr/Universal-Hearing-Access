#!/usr/bin/env python3
"""
live_plot.py
Run this on your Linux computer to display live audio waveform from TWO mics on Pico.

Usage:
    python3 live_plot.py [serial_port]
    
Example:
    python3 live_plot.py /dev/ttyACM0
"""

import sys
import serial
import serial.tools.list_ports
from collections import deque
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Configuration
BAUD_RATE = 115200
BUFFER_SIZE = 500  # Number of samples to display (5 seconds at 100 Hz)
UPDATE_INTERVAL_MS = 50  # Graph refresh rate (20 FPS)

# Voltage range for MAX4466 (centered around ~1.65V at silence)
VOLTAGE_MIN = 0.0
VOLTAGE_MAX = 3.3


def find_pico_port():
    """Auto-detect the Pico's serial port."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'ttyACM' in port.device or 'usbmodem' in port.device:
            print(f"Found potential Pico at: {port.device}")
            return port.device
    return None


def main():
    # Determine serial port
    if len(sys.argv) > 1:
        port_name = sys.argv[1]
    else:
        port_name = find_pico_port()
        if port_name is None:
            print("Error: Could not auto-detect Pico.")
            print("Available ports:")
            for port in serial.tools.list_ports.comports():
                print(f"  {port.device} - {port.description}")
            print("\nUsage: python3 live_plot.py /dev/ttyACM0")
            sys.exit(1)
    
    print(f"Connecting to {port_name}...")
    
    try:
        ser = serial.Serial(port_name, BAUD_RATE, timeout=0.1)
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        print("\nTips:")
        print("  - Make sure Thonny is closed (it locks the port)")
        print("  - Check if you have permission: sudo usermod -a -G dialout $USER")
        print("  - Then log out and back in")
        sys.exit(1)
    
    print("Connected! Reading data...")
    
    # Data buffers for both mics (circular buffers)
    voltage_left = deque([1.65] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
    voltage_right = deque([1.65] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
    time_data = list(range(BUFFER_SIZE))
    
    # Debug counters
    total_samples = [0]
    empty_frames = [0]
    
    # Set up the plot with a dark theme - TWO subplots
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    fig.canvas.manager.set_window_title('Pico Dual Microphone - Live Audio')
    
    # Create line objects for both mics
    line_left, = ax1.plot(time_data, list(voltage_left), 
                          color='#00ff88', linewidth=1.5, alpha=0.9)
    line_right, = ax2.plot(time_data, list(voltage_right), 
                           color='#ff6b6b', linewidth=1.5, alpha=0.9)
    
    # Add center reference lines (silence level ~1.65V)
    ax1.axhline(y=1.65, color='#555555', linestyle='--', linewidth=1, alpha=0.7)
    ax2.axhline(y=1.65, color='#555555', linestyle='--', linewidth=1, alpha=0.7)
    
    # Configure axes - Left mic (GP28)
    ax1.set_xlim(0, BUFFER_SIZE)
    ax1.set_ylim(VOLTAGE_MIN, VOLTAGE_MAX)
    ax1.set_ylabel('Voltage (V)', fontsize=11)
    ax1.set_title('Left Mic (INMP441)', fontsize=13, fontweight='bold', color='#00ff88')
    ax1.grid(True, alpha=0.3)
    
    # Configure axes - Right mic (GP27)
    ax2.set_xlim(0, BUFFER_SIZE)
    ax2.set_ylim(VOLTAGE_MIN, VOLTAGE_MAX)
    ax2.set_xlabel('Sample', fontsize=11)
    ax2.set_ylabel('Voltage (V)', fontsize=11)
    ax2.set_title('Right Mic (INMP441)', fontsize=13, fontweight='bold', color='#ff6b6b')
    ax2.grid(True, alpha=0.3)
    
    # Voltage level indicator text for both
    level_text_left = ax1.text(0.02, 0.95, '', transform=ax1.transAxes, 
                               fontsize=10, verticalalignment='top',
                               color='#00ff88', fontfamily='monospace')
    level_text_right = ax2.text(0.02, 0.95, '', transform=ax2.transAxes, 
                                fontsize=10, verticalalignment='top',
                                color='#ff6b6b', fontfamily='monospace')
    
    print("Displaying graph. Close the window to exit.")
    print("Waiting for data from Pico...")
    
    def update(frame):
        """Animation update function - called every frame."""
        samples_read = 0
        while ser.in_waiting > 0:
            try:
                line_data = ser.readline().decode('utf-8').strip()
                if line_data and ',' in line_data:
                    parts = line_data.split(',')
                    if len(parts) == 2:
                        v_left = float(parts[0])
                        v_right = float(parts[1])
                        voltage_left.append(v_left)
                        voltage_right.append(v_right)
                        samples_read += 1
                        
                        # Debug: print every 10th sample to terminal
                        if samples_read % 10 == 1:
                            print(f"Left: {v_left:.4f}V  |  Right: {v_right:.4f}V")
            except (ValueError, UnicodeDecodeError) as e:
                print(f"Bad data: '{line_data}' - {e}")
        
        # Update the plots
        if samples_read > 0:
            total_samples[0] += samples_read
            empty_frames[0] = 0
            
            line_left.set_ydata(list(voltage_left))
            line_right.set_ydata(list(voltage_right))
            
            # Calculate and display current levels - Left
            curr_left = voltage_left[-1]
            amp_left = max(voltage_left) - min(voltage_left)
            level_text_left.set_text(
                f'Current: {curr_left:.3f}V | P-P: {amp_left:.3f}V'
            )
            
            # Calculate and display current levels - Right
            curr_right = voltage_right[-1]
            amp_right = max(voltage_right) - min(voltage_right)
            level_text_right.set_text(
                f'Current: {curr_right:.3f}V | P-P: {amp_right:.3f}V'
            )
        else:
            empty_frames[0] += 1
            if empty_frames[0] == 40:
                print(f"Warning: No data received! Total samples so far: {total_samples[0]}")
                print(f"  - Is the Pico running main.py?")
                print(f"  - Try unplugging and replugging the Pico")
                empty_frames[0] = 0
        
        return line_left, line_right, level_text_left, level_text_right
    
    # Create animation
    ani = animation.FuncAnimation(
        fig, update, interval=UPDATE_INTERVAL_MS, blit=True, cache_frame_data=False
    )
    
    try:
        plt.tight_layout()
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        print("Serial port closed.")


if __name__ == '__main__':
    main()
