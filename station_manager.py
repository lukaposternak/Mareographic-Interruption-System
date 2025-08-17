from interruption_system import InterruptionSystem
import time
from contextlib import contextmanager

class StationManager:
    def __init__(self):
        self.stations = {}
    
    def add_station(self, station_id: str, custom_config: dict = None):
        """Adds a new station to the system"""
        system = InterruptionSystem(station_id)
        if custom_config:
            system.update_configuration(**custom_config)
        self.stations[station_id] = system
        print(f"✅ Station {station_id} added")
        return system

    @contextmanager
    def run_all_stations(self):
        """Context manager for automatic station management"""
        try:
            self.start_all_stations()
            yield self
        finally:
            self.stop_all_stations()

    def start_all_stations(self):
        """Starts all stations"""
        print("🌊 Starting all stations...")
        for station_id, system in self.stations.items():
            system.start_system()
            time.sleep(0.5)
        print(f"✅ {len(self.stations)} stations started")

    def stop_all_stations(self):
        """Stops all stations"""
        print("\n🛑 Stopping all stations...")
        for station_id, system in self.stations.items():
            system.stop_system()
        print("✅ All stations stopped")

    def show_general_summary(self):
        """Shows a summary of all stations"""
        print("\n" + "="*70)
        print("📊 GENERAL STATION SUMMARY")
        print("="*70)
        
        total_interruptions = 0
        for station_id, system in self.stations.items():
            state = system.get_system_state()
            stats = state['statistics']
            
            print(f"\n📍 Station: {station_id}")
            print(f"   State: {'🟢 Active' if state['running'] else '🔴 Inactive'}")
            print(f"   Total interruptions: {stats['total_interruptions']}")
            print(f"   ├─ Sensor failures: {stats['sensor_failure']}")
            print(f"   ├─ Extreme conditions: {stats['extreme_conditions']}")
            
            total_interruptions += stats['total_interruptions']
        
        print(f"\n🔢 SYSTEM TOTAL: {total_interruptions} interruptions")
        print("="*70)