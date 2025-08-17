from mareographic_system.interruption_system import InterruptionMonitor

def main():
    monitor = InterruptionMonitor()
    monitor.run()

if __name__ == "__main__":
    main()