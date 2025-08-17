"""
Mareographic Interruption System using Signals
"""

import time
import random
import signal
import threading
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Callable, Any
from contextlib import contextmanager
from mareographic_system.interruption_system import InterruptionMonitor


# 1. SYSTEM BASE DEFINITIONS
class InterruptionType(Enum):
    SENSOR_FAILURE = signal.SIGINT        # Ctrl+C (High priority)
    EXTREME_CONDITIONS = signal.SIGBREAK  # Ctrl+Break (Medium priority)

class SensorState(Enum):
    FUNCTIONING = "functioning"
    READ_FAILURE = "read_failure"
    DISCONNECTED = "disconnected"

@dataclass
class Interruption:
    type: InterruptionType
    timestamp: datetime
    station_id: str
    message: str
    sensor_data: dict

@dataclass
class SensorData:
    water_level: float    # meters
    temperature: float   # celsius
    pressure: float       # hPa
    wind_speed: float  # km/h
    state: SensorState
    timestamp: datetime

# 2. MAIN SYSTEM CLASS
class InterruptionSystem:
    def __init__(self, station_id: str):
        self.monitor = InterruptionMonitor()
        self.station_id = station_id
        self.running = False
        self.monitor_thread = None
        self.handlers = {}  # Dictionary to store handlers
        self._shutdown_requested = False
        
        # Threshold configuration
        self.config = {
            'high_tide_threshold': 2.5,      # meters
            'extreme_tide_threshold': 4.0,   # meters
            'extreme_temp_min': -5.0,      # celsius
            'extreme_temp_max': 35.0,      # celsius
            'extreme_wind_max': 120.0,   # km/h
            'min_reading_interval': 0.5,  # seconds
            'max_reading_interval': 3.0   # seconds
        }
        
        # Statistics
        self.statistics = {
            'total_interruptions': 0,
            'high_tide': 0,
            'sensor_failure': 0,
            'extreme_conditions': 0
        }
    
    def _handle_shutdown(self, signum, frame):
        """Dedicated handler for termination signals"""
        print(f"\n🔴 Termination signal received ({signal.Signals(signum).name})")
        self._shutdown_requested = True
        self.running = False
    
    def update_configuration(self, **kwargs):
        """Allows real-time configuration updates"""
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
                print(f"✅ Configuration updated: {key} = {value}")
            else:
                print(f"❌ Invalid parameter: {key}")

    def get_system_state(self) -> Dict:
        """Returns current system state"""
        return {
            'running': self.running,
            'statistics': self.statistics.copy(),
            'configuration': self.config.copy()
        }
    
    @contextmanager
    def execute(self):
        """Context manager for automatic start/stop management"""
        try:
            self.start_system()
            yield self  # This allows using 'with system.execute() as s:'
        finally:
            self.stop_system()
            
    def register_handler(self, type: InterruptionType, handler: Callable[[Interruption], Any]):
        """Registers a handler for an interruption type"""
        self.handlers[type] = handler
        signal.signal(type.value, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Generic signal handler that delegates to specific handler"""
        type = InterruptionType(signum)
        if type in self.handlers:
            # Retrieve generated interruption
            interruption = getattr(self, '_last_interruption', None)
            if interruption:
                self.handlers[type](interruption)

    def start_system(self):
        """Starts monitoring system"""
        print(f"🌊 Starting Interruption System - Station: {self.station_id}")
        print("=" * 60)
    
        self.running = True
        self._shutdown_requested = False
    
        # Configure signal handling
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
        # Thread for sensor monitoring
        self.monitor_thread = threading.Thread(target=self._monitor_sensors)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_system(self):
        """Stops monitoring system"""
        if not self.running:
            return
    
        print("\n🛑 Stopping system...")
        self.running = False
        self._shutdown_requested = True
    
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
    
        # Restore signal handlers
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
    
        print("✅ System stopped")
        self._show_final_statistics()

    def _simulate_sensor_reading(self) -> SensorData:
        """Simulates mareographic sensor reading"""
        # Simulate possible sensor failures (5% probability)
        if random.random() < 0.05:
            state = random.choice([SensorState.READ_FAILURE, SensorState.DISCONNECTED])
            return SensorData(
                water_level=0.0,
                temperature=0.0,
                pressure=0.0,
                wind_speed=0.0,
                state=state,
                timestamp=datetime.now()
            )
        
        # Generate realistic data with variations
        base_level = 1.5
        tide_variation = random.uniform(-0.8, 2.0)  # Tide variation
        
        # Occasionally generate extreme conditions
        if random.random() < 0.1:  # 10% probability of extreme conditions
            water_level = base_level + random.uniform(3.0, 5.0)
            temperature = random.choice([
                random.uniform(-10, self.config['extreme_temp_min']),
                random.uniform(self.config['extreme_temp_max'], 45)
            ])
            wind = random.uniform(100, 150)
        else:
            water_level = base_level + tide_variation
            temperature = random.uniform(10, 25)
            wind = random.uniform(5, 40)
        
        return SensorData(
            water_level=round(water_level, 2),
            temperature=round(temperature, 1),
            pressure=round(random.uniform(1000, 1030), 1),
            wind_speed=round(wind, 1),
            state=SensorState.FUNCTIONING,
            timestamp=datetime.now()
        )

    def _evaluate_conditions(self, data: SensorData):
        """Evaluates conditions and generates interruptions (signals) according to priority"""
        # PRIORITY 1: Sensor failure
        if data.state != SensorState.FUNCTIONING:
            self._generate_interruption(
                InterruptionType.SENSOR_FAILURE,
                f"⚠ SENSOR FAILURE: {data.state.value}",
                data
            )
            return
        
        # PRIORITY 2: Extreme conditions or high tide
        extreme_conditions = []
        if data.water_level >= self.config['extreme_tide_threshold']:
            extreme_conditions.append(f"Extreme tide: {data.water_level}m")
        elif data.water_level >= self.config['high_tide_threshold']:
            extreme_conditions.append(f"High tide: {data.water_level}m")
        
        if data.temperature <= self.config['extreme_temp_min']:
            extreme_conditions.append(f"Extreme low temp: {data.temperature}°C")
        elif data.temperature >= self.config['extreme_temp_max']:
            extreme_conditions.append(f"Extreme high temp: {data.temperature}°C")
            
        if data.wind_speed >= self.config['extreme_wind_max']:
            extreme_conditions.append(f"Extreme wind: {data.wind_speed}km/h")
        
        if extreme_conditions:
            self._generate_interruption(
                InterruptionType.EXTREME_CONDITIONS,
                f"🚨 {' | '.join(extreme_conditions)}",
                data
            )

    def _generate_interruption(self, type: InterruptionType, message: str, data: SensorData):
        """Generates an interruption (sends signal)"""
        interruption = Interruption(
            type=type,
            timestamp=datetime.now(),
            station_id=self.station_id,
            message=message,
            sensor_data=data.__dict__.copy()
        )
        self.monitor.handle_interruption(interruption)
        
        # Save interruption so handler can access it
        self._last_interruption = interruption
        
        # Send signal to current process
        signal.raise_signal(type.value)
        
        # Update statistics
        self.statistics['total_interruptions'] += 1
        if type == InterruptionType.SENSOR_FAILURE:
            self.statistics['sensor_failure'] += 1
        elif type == InterruptionType.EXTREME_CONDITIONS:
            self.statistics['extreme_conditions'] += 1

    def _monitor_sensors(self):
        """Main sensor monitoring thread"""
        while self.running and not self._shutdown_requested:
            try:
                # Simulate sensor reading
                data = self._simulate_sensor_reading()
                
                # Evaluate conditions and generate interruptions (signals)
                self._evaluate_conditions(data)
                
                # Show current state (only if sensor is functioning)
                if data.state == SensorState.FUNCTIONING:
                    self._show_normal_state(data)
                
                # Sleep for a random interval
                interval = random.uniform(
                    self.config['min_reading_interval'],
                    self.config['max_reading_interval']
                )
                time.sleep(interval)
                # Check if shutdown was requested during sleep
                for _ in range(int(interval * 10)):
                    if self._shutdown_requested:
                        break
                    time.sleep(0.1)
                
            except Exception as e:
                if not self._shutdown_requested:
                    print(f"❌ Monitoring error: {e}")
                time.sleep(1)

    def _show_normal_state(self, data: SensorData):
        """Shows normal sensor state"""
        timestamp_str = data.timestamp.strftime("%H:%M:%S")
        
        # Show only every 10 readings to avoid screen saturation
        if random.random() < 0.1:
            print(f"📊 [{timestamp_str}] Level: {data.water_level}m | "
                  f"Temp: {data.temperature}°C | "
                  f"Wind: {data.wind_speed}km/h | "
                  f"Pressure: {data.pressure}hPa")

    def _show_final_statistics(self):
        """Shows final system statistics"""
        print("\n" + "="*50)
        print("📈 FINAL STATISTICS")
        print("="*50)
        print(f"Total interruptions: {self.statistics['total_interruptions']}")
        print(f"├─ Sensor failures: {self.statistics['sensor_failure']}")
        print(f"├─ Extreme conditions: {self.statistics['extreme_conditions']}")
        print("="*50)


    def show_configuration(self):
        """Shows current system configuration"""
        print("\n⚙  CURRENT CONFIGURATION")
        print("-" * 40)
        print(f"High tide threshold: {self.config['high_tide_threshold']} m")
        print(f"Extreme tide threshold: {self.config['extreme_tide_threshold']} m")
        print(f"Extreme minimum temperature: {self.config['extreme_temp_min']} °C")
        print(f"Extreme maximum temperature: {self.config['extreme_temp_max']} °C")
        print(f"Extreme maximum wind: {self.config['extreme_wind_max']} km/h")
        print(f"Reading interval: {self.config['min_reading_interval']}-{self.config['max_reading_interval']} seconds")
        print("-" * 40)