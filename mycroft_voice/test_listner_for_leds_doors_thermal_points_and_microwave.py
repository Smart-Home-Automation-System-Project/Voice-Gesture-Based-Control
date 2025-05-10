from speech_recognition import Recognizer, Microphone
import time
import os
import RPi.GPIO as GPIO
import random  # For simulating sensor readings

# GPIO Setup
# Light pins
L1_PIN = 17
L2_PIN = 27
L3_PIN = 22
L4_PIN = 23

# Door servo pins
D1_PIN = 18
D2_PIN = 24
D3_PIN = 25

# Microwave control pins
MW_POWER_PIN = 5    # Relay for power control
MW_LIGHT_PIN = 6    # Microwave light
MW_TURNTABLE_PIN = 13  # Turntable motor
MW_MAGNETRON_PIN = 19  # Simulating magnetron control

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Initialize light outputs
GPIO.setup(L1_PIN, GPIO.OUT)
GPIO.setup(L2_PIN, GPIO.OUT)
GPIO.setup(L3_PIN, GPIO.OUT)
GPIO.setup(L4_PIN, GPIO.OUT)

# Turn all lights off initially
GPIO.output(L1_PIN, GPIO.LOW)
GPIO.output(L2_PIN, GPIO.LOW)
GPIO.output(L3_PIN, GPIO.LOW)
GPIO.output(L4_PIN, GPIO.LOW)

# Initialize door servos
GPIO.setup(D1_PIN, GPIO.OUT)
GPIO.setup(D2_PIN, GPIO.OUT)
GPIO.setup(D3_PIN, GPIO.OUT)

# Create PWM instances for doors
d1_servo = GPIO.PWM(D1_PIN, 50)  # 50Hz PWM frequency
d2_servo = GPIO.PWM(D2_PIN, 50)
d3_servo = GPIO.PWM(D3_PIN, 50)

# Start all servos
d1_servo.start(0)
d2_servo.start(0)
d3_servo.start(0)

# Initialize microwave controls
GPIO.setup(MW_POWER_PIN, GPIO.OUT)
GPIO.setup(MW_LIGHT_PIN, GPIO.OUT)
GPIO.setup(MW_TURNTABLE_PIN, GPIO.OUT)
GPIO.setup(MW_MAGNETRON_PIN, GPIO.OUT)

# Turn off microwave initially
GPIO.output(MW_POWER_PIN, GPIO.LOW)
GPIO.output(MW_LIGHT_PIN, GPIO.LOW)
GPIO.output(MW_TURNTABLE_PIN, GPIO.LOW)
GPIO.output(MW_MAGNETRON_PIN, GPIO.LOW)

# Thermal Stat Settings
class ThermalStat:
    def __init__(self, id):
        self.id = id
        self.current_temp = 22.0  # Default temperature
        self.current_humidity = 50.0  # Default humidity
        self.target_temp = 22.0
        self.target_humidity = 50.0
        self.temp_range = (18.0, 30.0)  # Min, Max temperature
        self.humidity_range = (30.0, 70.0)  # Min, Max humidity
        self.temp_step = 1.0
        self.humidity_step = 5.0
    
    def update(self):
        """Simulate sensor reading changes"""
        # Small random fluctuations
        self.current_temp += random.uniform(-0.5, 0.5)
        self.current_humidity += random.uniform(-2, 2)
        
        # Keep within physical limits
        self.current_temp = max(self.temp_range[0], min(self.temp_range[1], self.current_temp))
        self.current_humidity = max(self.humidity_range[0], min(self.humidity_range[1], self.current_humidity))
        
        # Gradually move toward target (simulating HVAC system)
        if abs(self.current_temp - self.target_temp) > 0.2:
            direction = 1 if self.target_temp > self.current_temp else -1
            self.current_temp += direction * 0.1
        
        if abs(self.current_humidity - self.target_humidity) > 1:
            direction = 1 if self.target_humidity > self.current_humidity else -1
            self.current_humidity += direction * 0.5
    
    def set_temp(self, temp):
        if self.temp_range[0] <= temp <= self.temp_range[1]:
            self.target_temp = temp
            return True
        return False
    
    def set_humidity(self, humidity):
        if self.humidity_range[0] <= humidity <= self.humidity_range[1]:
            self.target_humidity = humidity
            return True
        return False
    
    def temp_up(self):
        return self.set_temp(self.target_temp + self.temp_step)
    
    def temp_down(self):
        return self.set_temp(self.target_temp - self.temp_step)
    
    def humidity_up(self):
        return self.set_humidity(self.target_humidity + self.humidity_step)
    
    def humidity_down(self):
        return self.set_humidity(self.target_humidity - self.humidity_step)
    
    def status(self):
        return (f"Thermal Stat {self.id}:\n"
                f"  Temperature: {self.current_temp:.1f}°C (Target: {self.target_temp:.1f}°C)\n"
                f"  Humidity:    {self.current_humidity:.1f}% (Target: {self.target_humidity:.1f}%)")

# Initialize 3 thermal stats
thermal_stats = [ThermalStat(i+1) for i in range(3)]

# Microwave Oven Class
class MicrowaveOven:
    def __init__(self):
        self.power_levels = {
            'high': 100,
            'medium': 70,
            'low': 40,
            'defrost': 30
        }
        self.current_power = 'high'
        self.is_running = False
        self.time_remaining = 0
        self.door_open = False
        self.light_on = False
        self.turntable_on = False
        
    def start(self, seconds, power_level=None):
        """Start the microwave with specified time and power level"""
        if self.door_open:
            print("⚠️ Cannot start microwave with door open")
            return False
            
        if power_level:
            if power_level.lower() in self.power_levels:
                self.current_power = power_level.lower()
            else:
                print(f"⚠️ Invalid power level. Using {self.current_power}")
                
        self.time_remaining = seconds
        self.is_running = True
        self.light_on = True
        self.turntable_on = True
        
        # Activate hardware
        GPIO.output(MW_LIGHT_PIN, GPIO.HIGH)
        GPIO.output(MW_TURNTABLE_PIN, GPIO.HIGH)
        GPIO.output(MW_MAGNETRON_PIN, GPIO.HIGH if self.current_power == 'high' else GPIO.LOW)
        
        print(f"♨️ Microwave started for {seconds} seconds at {self.current_power} power")
        return True
        
    def stop(self):
        """Stop the microwave"""
        self.is_running = False
        self.time_remaining = 0
        self.light_on = False
        
        # Deactivate hardware (except light if door is open)
        GPIO.output(MW_LIGHT_PIN, GPIO.HIGH if self.door_open else GPIO.LOW)
        GPIO.output(MW_TURNTABLE_PIN, GPIO.LOW)
        GPIO.output(MW_MAGNETRON_PIN, GPIO.LOW)
        
        print("⏹️ Microwave stopped")
        
    def pause(self):
        """Pause the microwave"""
        if self.is_running:
            self.is_running = False
            GPIO.output(MW_MAGNETRON_PIN, GPIO.LOW)
            print("⏸️ Microwave paused")
        
    def resume(self):
        """Resume paused microwave"""
        if not self.is_running and self.time_remaining > 0:
            self.is_running = True
            GPIO.output(MW_MAGNETRON_PIN, GPIO.HIGH if self.current_power == 'high' else GPIO.LOW)
            print("▶️ Microwave resumed")
            
    def set_power(self, level):
        """Set microwave power level"""
        if level.lower() in self.power_levels:
            self.current_power = level.lower()
            print(f"⚡ Microwave power set to {self.current_power}")
            return True
        else:
            print(f"⚠️ Invalid power level. Available levels: {', '.join(self.power_levels.keys())}")
            return False
            
    def open_door(self):
        """Open microwave door"""
        self.door_open = True
        self.light_on = True
        if self.is_running:
            self.pause()
        GPIO.output(MW_LIGHT_PIN, GPIO.HIGH)
        print("🚪 Microwave door opened")
        
    def close_door(self):
        """Close microwave door"""
        self.door_open = False
        self.light_on = self.is_running
        GPIO.output(MW_LIGHT_PIN, GPIO.HIGH if self.is_running else GPIO.LOW)
        print("🚪 Microwave door closed")
        
    def add_time(self, seconds):
        """Add time to microwave"""
        if self.is_running:
            self.time_remaining += seconds
            print(f"⏱️ Added {seconds} seconds. Total time remaining: {self.time_remaining} seconds")
            return True
        return False
        
    def status(self):
        """Return microwave status"""
        return (f"Microwave Oven:\n"
                f"  State:       {'Running' if self.is_running else 'Idle'}\n"
                f"  Door:        {'Open' if self.door_open else 'Closed'}\n"
                f"  Power Level: {self.current_power.capitalize()}\n"
                f"  Time Remaining: {self.time_remaining} seconds\n"
                f"  Light:       {'On' if self.light_on else 'Off'}\n"
                f"  Turntable:   {'On' if self.turntable_on else 'Off'}")

# Initialize microwave
microwave = MicrowaveOven()

def set_door(door_num, position):
    """Control servo to open/close specific door"""
    servo = None
    if door_num == 1:
        servo = d1_servo
    elif door_num == 2:
        servo = d2_servo
    elif door_num == 3:
        servo = d3_servo
    
    if servo:
        if position == "open":
            servo.ChangeDutyCycle(7.5)  # 90 degrees (open position)
            print(f"🚪 Door {door_num} opened")
        elif position == "close":
            servo.ChangeDutyCycle(2.5)  # 0 degrees (closed position)
            print(f"🚪 Door {door_num} closed")
        time.sleep(1)  # Give servo time to move
        servo.ChangeDutyCycle(0)  # Stop sending signal

def set_all_doors(position):
    """Control all doors at once"""
    for door_num in range(1, 4):
        set_door(door_num, position)

def set_light(light_num, state):
    """Control specific light"""
    pin = None
    if light_num == 1:
        pin = L1_PIN
    elif light_num == 2:
        pin = L2_PIN
    elif light_num == 3:
        pin = L3_PIN
    elif light_num == 4:
        pin = L4_PIN
    
    if pin:
        GPIO.output(pin, GPIO.HIGH if state == "on" else GPIO.LOW)
        print(f"💡 Light {light_num} turned {'ON' if state == 'on' else 'OFF'}")

def set_all_lights(state):
    """Control all lights at once"""
    for light_num in range(1, 5):
        set_light(light_num, state)

def process_thermal_command(stat_num, command):
    """Handle thermal stat commands"""
    if stat_num < 1 or stat_num > 3:
        print(f"⚠️ Invalid thermal stat number: {stat_num}")
        return
    
    ts = thermal_stats[stat_num - 1]
    command = command.lower()
    
    try:
        if "temp up" in command:
            if ts.temp_up():
                print(f"🌡️ Thermal Stat {stat_num} temperature increased to {ts.target_temp:.1f}°C")
            else:
                print(f"⚠️ Cannot increase beyond maximum temperature {ts.temp_range[1]}°C")
        
        elif "temp down" in command:
            if ts.temp_down():
                print(f"🌡️ Thermal Stat {stat_num} temperature decreased to {ts.target_temp:.1f}°C")
            else:
                print(f"⚠️ Cannot decrease below minimum temperature {ts.temp_range[0]}°C")
        
        elif "humidity up" in command:
            if ts.humidity_up():
                print(f"💧 Thermal Stat {stat_num} humidity increased to {ts.target_humidity:.1f}%")
            else:
                print(f"⚠️ Cannot increase beyond maximum humidity {ts.humidity_range[1]}%")
        
        elif "humidity down" in command:
            if ts.humidity_down():
                print(f"💧 Thermal Stat {stat_num} humidity decreased to {ts.target_humidity:.1f}%")
            else:
                print(f"⚠️ Cannot decrease below minimum humidity {ts.humidity_range[0]}%")
        
        elif "set temp" in command:
            # Extract temperature value from command
            words = command.split()
            for word in words:
                if word.replace('.', '').isdigit():
                    temp = float(word)
                    if ts.set_temp(temp):
                        print(f"🌡️ Thermal Stat {stat_num} temperature set to {temp:.1f}°C")
                    else:
                        print(f"⚠️ Temperature must be between {ts.temp_range[0]} and {ts.temp_range[1]}°C")
                    break
            else:
                print("⚠️ Please specify a temperature value (e.g., 'T1 SET TEMP 22')")
        
        elif "set humidity" in command:
            # Extract humidity value from command
            words = command.split()
            for word in words:
                if word.replace('.', '').isdigit():
                    humidity = float(word)
                    if ts.set_humidity(humidity):
                        print(f"💧 Thermal Stat {stat_num} humidity set to {humidity:.1f}%")
                    else:
                        print(f"⚠️ Humidity must be between {ts.humidity_range[0]} and {ts.humidity_range[1]}%")
                    break
            else:
                print("⚠️ Please specify a humidity value (e.g., 'T1 SET HUMIDITY 50')")
        
        elif "show" in command:
            print(ts.status())
        
        else:
            print(f"⚠️ Unknown thermal stat command. Try:\n"
                  f"  'T{stat_num} TEMP UP/DOWN'\n"
                  f"  'T{stat_num} HUMIDITY UP/DOWN'\n"
                  f"  'T{stat_num} SET TEMP X'\n"
                  f"  'T{stat_num} SET HUMIDITY X'\n"
                  f"  'T{stat_num} SHOW'")
    
    except ValueError:
        print("⚠️ Invalid number format")

def process_microwave_command(command):
    """Handle microwave oven commands"""
    command = command.lower()
    
    try:
        if "start" in command or "cook" in command:
            # Extract time and power level
            time_seconds = 30  # Default
            power_level = None
            
            # Look for time in command (e.g., "30 seconds", "1 minute")
            words = command.split()
            for i, word in enumerate(words):
                if word.isdigit():
                    # Check next word for time unit
                    if i+1 < len(words) and "second" in words[i+1]:
                        time_seconds = int(word)
                    elif i+1 < len(words) and "minute" in words[i+1]:
                        time_seconds = int(word) * 60
                    else:
                        # Assume seconds if no unit specified
                        time_seconds = int(word)
            
            # Look for power level
            for level in microwave.power_levels:
                if level in command:
                    power_level = level
                    break
                    
            microwave.start(time_seconds, power_level)
            
        elif "stop" in command or "cancel" in command:
            microwave.stop()
            
        elif "pause" in command:
            microwave.pause()
            
        elif "resume" in command or "continue" in command:
            microwave.resume()
            
        elif "power" in command:
            # Set power level
            for level in microwave.power_levels:
                if level in command:
                    microwave.set_power(level)
                    break
            else:
                print("⚠️ Please specify power level (high, medium, low, defrost)")
                
        elif "open" in command and "door" in command:
            microwave.open_door()
            
        elif "close" in command and "door" in command:
            microwave.close_door()
            
        elif "add" in command and ("time" in command or "seconds" in command or "minute" in command):
            # Extract time to add
            words = command.split()
            for i, word in enumerate(words):
                if word.isdigit():
                    # Check next word for time unit
                    if i+1 < len(words) and "second" in words[i+1]:
                        seconds = int(word)
                    elif i+1 < len(words) and "minute" in words[i+1]:
                        seconds = int(word) * 60
                    else:
                        # Assume seconds if no unit specified
                        seconds = int(word)
                        
                    microwave.add_time(seconds)
                    break
            else:
                print("⚠️ Please specify time to add (e.g., 'add 30 seconds')")
                
        elif "status" in command or "show" in command:
            print(microwave.status())
            
        else:
            print("⚠️ Unknown microwave command. Try:\n"
                  "  'Start microwave for 30 seconds'\n"
                  "  'Cook for 1 minute at medium power'\n"
                  "  'Stop microwave'\n"
                  "  'Pause microwave'\n"
                  "  'Resume microwave'\n"
                  "  'Set power to high'\n"
                  "  'Open microwave door'\n"
                  "  'Close microwave door'\n"
                  "  'Add 30 seconds'\n"
                  "  'Microwave status'")
    
    except Exception as e:
        print(f"⚠️ Error processing microwave command: {e}")

def get_microphone_index():
    """Try to find the correct microphone index"""
    try:
        print("Available microphones:")
        for index, name in enumerate(Microphone.list_microphone_names()):
            print(f"{index}: {name}")
            
        for index, name in enumerate(Microphone.list_microphone_names()):
            if "analog" in name.lower() or "input" in name.lower():
                print(f"\n🔊 Selecting microphone: {name} (index {index})")
                return index
                
        print("\n Couldn't find analog input, using default (index 0)")
        return 0
    except:
        return 0

def listen_for_command(prompt=None, timeout=3):
    recognizer = Recognizer()
    mic_index = get_microphone_index()
    
    try:
        with Microphone(device_index=mic_index) as source:
            if prompt:
                print(prompt)
            print("(Listening... say your command)", end=" ", flush=True)
            
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=timeout)
            
        return recognizer.recognize_google(audio).lower()
    except Exception as e:
        if "wait_timeout" in str(e):
            print("⏰ Timeout - Didn't hear anything")
        elif "UnknownValueError" in str(e):
            print("🔇 Couldn't understand audio")
        else:
            print(f"❌ Error: {e}")
        return None

def process_command(command):
    """Process voice commands for lights, doors, thermal stats, and microwave"""
    if not command:
        return
        
    print(f"\n✅ You said: {command}")
    
    # Process light commands
    if "all on" in command:
        set_all_lights("on")
    elif "all off" in command:
        set_all_lights("off")
    else:
        for i in range(1, 5):
            if f"l{i} on" in command or f"light {i} on" in command:
                set_light(i, "on")
            elif f"l{i} off" in command or f"light {i} off" in command:
                set_light(i, "off")
    
    # Process door commands
    if "all open" in command:
        set_all_doors("open")
    elif "all close" in command:
        set_all_doors("close")
    else:
        for i in range(1, 4):
            if f"d{i} open" in command or f"door {i} open" in command:
                set_door(i, "open")
            elif f"d{i} close" in command or f"door {i} close" in command:
                set_door(i, "close")
            elif "open" in command and f"door {i}" in command:
                set_door(i, "open")
            elif "close" in command and f"door {i}" in command:
                set_door(i, "close")
    
    # Process thermal stat commands
    for i in range(1, 4):
        if f"t{i}" in command:
            process_thermal_command(i, command)
    
    # Process microwave commands
    if "microwave" in command or "oven" in command:
        process_microwave_command(command)

def update_system():
    """Update system state (called in main loop)"""
    # Update thermal stats
    for ts in thermal_stats:
        ts.update()
    
    # Update microwave timer
    if microwave.is_running:
        microwave.time_remaining = max(0, microwave.time_remaining - 1)
        if microwave.time_remaining == 0:
            microwave.stop()

if __name__ == "__main__":
    print("\n🏠 Raspberry Pi Voice Control System")
    print("----------------------------------")
    print("Available commands:")
    print("  - Lights:")
    print("     * Individual: 'L1 ON', 'LIGHT 2 OFF', etc.")
    print("     * All: 'ALL ON', 'ALL OFF'")
    print("  - Doors:")
    print("     * Individual: 'D1 OPEN', 'DOOR 2 CLOSE', etc.")
    print("     * All: 'ALL OPEN', 'ALL CLOSE'")
    print("  - Thermal Stats:")
    print("     * Adjust: 'T1 TEMP UP', 'T1 TEMP DOWN', 'T1 HUMIDITY UP', 'T1 HUMIDITY DOWN'")
    print("     * Status: 'T1 SHOW'")
    print("  - Microwave Oven:")
    print("     * 'Start microwave for 30 seconds'")
    print("     * 'Cook for 1 minute at medium power'")
    print("     * 'Stop microwave'")
    print("     * 'Open microwave door'")
    print("     * 'Microwave status'")
    print("Press Ctrl+C to exit\n")
    
    try:
        # Initialize all doors to closed position
        set_all_doors("close")
        
        # Main loop
        while True:
            command = listen_for_command("\n🎤 Say a command:")
            process_command(command)
            
            # Update system state
            update_system()
            
            # Small delay to prevent CPU overload
            time.sleep(0.1)
                
    except KeyboardInterrupt:
        print("\n👋 System shutting down...")
    finally:
        # Cleanup
        microwave.stop()
        d1_servo.stop()
        d2_servo.stop()
        d3_servo.stop()
        GPIO.cleanup()
        print("✅ GPIO cleanup complete")