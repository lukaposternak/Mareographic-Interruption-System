from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.table import Table
import threading
import time
import random
import signal
from datetime import datetime
from enum import Enum
from contextlib import contextmanager
from typing import Dict, Callable, Optional, NamedTuple
import msvcrt

class InterruptionType(Enum):
    SENSOR_FAILURE = signal.SIGINT
    EXTREME_CONDITIONS = signal.SIGBREAK

class Interruption(NamedTuple):
    type: InterruptionType
    message: str
    timestamp: datetime
    station_id: Optional[str] = None

class InterruptionMonitor:
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.interruption_history = Text()
        self.running = True
        self.simulation_active = False
        self.current_input = ""
        self.statistics = {
            'total_interruptions': 0,
            'sensor_failure': 0,
            'extreme_conditions': 0,
            'last_update': None
        }
        
        # Initial configuration
        self.config = {
            'high_tide_threshold': 2.5,
            'extreme_tide_threshold': 4.0,
            'min_simulation_interval': 1,
            'max_simulation_interval': 5,
            'sensor_failure_probability': 0.7
        }

        # Configure signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGBREAK, self._handle_signal)
        self.showing_submenu = False  
        self.current_menu_content = None  # To store current content
        self.last_summary_update = None  # To store the last generated summary

    def _handle_signal(self, signum, frame):
        """Signal handler that updates statistics"""
        type = InterruptionType(signum)
    
        # Update statistics
        self.statistics['total_interruptions'] += 1
        if type == InterruptionType.SENSOR_FAILURE:
            self.statistics['sensor_failure'] += 1
        else:
            self.statistics['extreme_conditions'] += 1
        self.statistics['last_update'] = datetime.now()
    
        # Rest of interruption handling code...
        message = "Sensor failure detected" if type == InterruptionType.SENSOR_FAILURE else "Extreme conditions detected"
        interruption = Interruption(
            type=type,
            message=message,
            timestamp=datetime.now()
        )
        self._update_history(interruption)

    def _update_history(self, interruption: Interruption):
        """Updates the interruption panel"""
        timestamp = interruption.timestamp.strftime("%H:%M:%S")
        
        if interruption.type == InterruptionType.SENSOR_FAILURE:
            style = "bold yellow"
            prefix = "⚠️ "
        else:
            style = "bold red"
            prefix = "🚨 "
        
        message = f"[{timestamp}] {interruption.message}"
        self.interruption_history.append(Text(f"{prefix}{message}\n", style=style))
        
        if len(self.interruption_history.split()) > 10:
            self.interruption_history = Text("\n").join(self.interruption_history.split()[-10:])

    def setup_layout(self):
        """Configures interface panels"""
        self.layout.split(
            Layout(name="menu", size=20),
            Layout(name="interruptions", ratio=1),
        )
        self._update_panels()

    def _update_panels(self):
        """Updates both panels showing clear instructions"""
        if self.current_menu_content and self.showing_submenu:
            self.layout["menu"].update(self.current_menu_content)
        else:
            menu_content = self._generate_menu_content()
            self.layout["menu"].update(Panel(menu_content, title="Main Menu", border_style="blue"))
    
        self.layout["interruptions"].update(Panel(self.interruption_history, title="[bold red]Interruptions", border_style="red"))

    def _generate_menu_content(self):
        """Generates menu content according to current state"""
        if self.current_menu_content and self.showing_submenu:
             self.current_menu_content
        
        menu = Text()
        menu.append("🌊 MAREOGRAPHIC INTERRUPTION SYSTEM\n", style="bold blue")
        menu.append("=====================================\n")
        menu.append("1. Show configuration\n")
        menu.append("2. Modify thresholds\n")
        menu.append("3. View statistics\n")
        menu.append("4. Show summary\n")
        menu.append("5. Exit\n")
    
        if self.current_input:
            menu.append(f"\nInput: {self.current_input}", style="bold green")
        else:
            menu.append("\nSelect an option (1-5): ", style="dim")
    
        return menu
    
    def _show_configuration(self):
        """Shows current configuration in a panel"""
        table = Table(title="Current Configuration", show_header=True, header_style="bold magenta")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", justify="right")
        
        for param, value in self.config.items():
            table.add_row(param.replace('_', ' ').title(), str(value))
        
        self.layout["menu"].update(Panel(table, title="Configuration", border_style="green"))

    def _modify_thresholds(self):
        """Allows modifying thresholds integrated with Rich interface"""
        self.current_input = ""  # Reset input
        self.showing_submenu = True
        selection = None
    
        # Show menu of modifiable parameters
        parameters = list(self.config.items())
    
        while self.running and selection is None:
            # Generate modification submenu content
            modification_menu = Text()
            modification_menu.append("📝 MODIFY THRESHOLDS\n", style="bold green")
            modification_menu.append("====================\n")
        
            for i, (param, value) in enumerate(parameters, 1):
                modification_menu.append(f"{i}. {param.replace('_', ' ').title()}: [yellow]{value}[/]\n")
        
            modification_menu.append("\nSelect parameter to modify (1-5) or 0 to return: ")
            modification_menu.append(f"\n> Input: {self.current_input}", style="bold green")
        
            self.current_menu_content = Panel(modification_menu, title="Modify Configuration", border_style="green")
            self._update_panels()
        
            # Process input
            if msvcrt.kbhit():
                char = msvcrt.getch().decode('utf-8', errors='ignore')
            
                if char in ('\r', '\n'):  # Enter
                    if self.current_input == "0":
                        self.current_menu_content = None
                        self.showing_submenu = False
                        return
                
                    if self.current_input.isdigit() and 1 <= int(self.current_input) <= len(parameters):
                        selection = int(self.current_input) - 1
                        self.current_input = ""  # Prepare for new input
                    else:
                        self.current_input = ""  # Reset invalid input
            
                elif char == '\x08':  # Backspace
                    self.current_input = self.current_input[:-1]
                elif char.isdigit():
                    self.current_input += char
            
                time.sleep(0.1)
    
        if selection is not None:
            self._modify_specific_parameter(parameters[selection][0], parameters[selection][1])

    def _modify_specific_parameter(self, parameter: str, current_value: float):
        """Handles modification of a specific parameter"""
        self.current_input = ""
        new_value = None
    
        while self.running and new_value is None:
            # Show modification interface
            edit_menu = Text()
            edit_menu.append(f"✏️ MODIFYING: {parameter.replace('_', ' ').title()}\n", style="bold cyan")
            edit_menu.append(f"Current value: [yellow]{current_value}[/]\n")
            edit_menu.append("\nEnter new value (0 to cancel): ")
            edit_menu.append(f"\n> Input: {self.current_input}", style="bold green")
        
            self.current_menu_content = Panel(edit_menu, title="Edit Parameter", border_style="cyan")
            self._update_panels()
        
            # Process input
            if msvcrt.kbhit():
                char = msvcrt.getch().decode('utf-8', errors='ignore')
            
                if char in ('\r', '\n'):  # Enter
                    if self.current_input == "0":
                        break
                
                    try:
                        new_value = float(self.current_input)
                        self.config[parameter] = new_value
                        self.console.print(f"[green]✓ {parameter} updated to {new_value}[/]")
                        time.sleep(1)  # Show confirmation message
                    except ValueError:
                        self.current_input = ""  # Reset invalid input
            
                elif char == '\x08':  # Backspace
                    self.current_input = self.current_input[:-1]
                elif char.isdigit() or char == '.':
                    self.current_input += char
            
                time.sleep(0.1)
    
        self.current_menu_content = None
        self.showing_submenu = False
    
    def _show_statistics(self):
        """Shows interruption statistics"""
        table = Table(title="Statistics", show_header=True, header_style="bold magenta")
        table.add_column("Type", style="cyan")
        table.add_column("Count", justify="right")
        
        table.add_row("Total Interruptions", str(self.statistics['total_interruptions']))
        table.add_row("Sensor Failures", str(self.statistics['sensor_failure']))
        table.add_row("Extreme Conditions", str(self.statistics['extreme_conditions']))
        
        self.layout["menu"].update(Panel(table, title="Statistics", border_style="green"))

    def _show_summary(self):
        """Shows a complete system summary"""
        summary = Text()
        summary.append("📊 SYSTEM SUMMARY\n", style="bold underline blue")
        summary.append(f"🔄 Total interruptions: {self.statistics['total_interruptions']}\n")
        summary.append(f"⚠️  Sensor failures: {self.statistics['sensor_failure']}\n")
        summary.append(f"🚨 Extreme conditions: {self.statistics['extreme_conditions']}\n")
        summary.append("\n⚙️ CURRENT CONFIGURATION\n", style="bold underline blue")
        
        for param, value in self.config.items():
            summary.append(f"{param.replace('_', ' ').title()}: {value}\n")
        
        self.layout["menu"].update(Panel(summary, title="System Summary", border_style="blue"))
    
    @contextmanager
    def run_simulation(self):
        """Context manager for simulation"""
        self.simulation_active = True
        simulation_thread = threading.Thread(target=self._simulate_interruptions, daemon=True)
        simulation_thread.start()
        try:
            yield
        finally:
            self.simulation_active = False
            simulation_thread.join()

    def _simulate_interruptions(self):
        """Generates random interruptions"""
        while self.simulation_active:
            time.sleep(random.uniform(1, 5))
            if random.random() < 0.7:
                signal.raise_signal(InterruptionType.SENSOR_FAILURE.value)
            else:
                signal.raise_signal(InterruptionType.EXTREME_CONDITIONS.value)

    def _check_input(self):
        """Enhanced keyboard input verification"""
        if not msvcrt.kbhit():
            return
    
        char = msvcrt.getch().decode('utf-8', errors='ignore')
    
        # Enter (confirm command)
        if char in ('\r', '\n'):
            if self.current_input:
                self._process_command(self.current_input)
    
        # Backspace (delete or go back)
        elif char == '\x08':
            if self.current_input:
                self.current_input = self.current_input[:-1]
            elif self.showing_submenu:
                self._process_command("0")  # Go back if no input in progress
    
        # Digits 0-5
        elif char.isdigit() and '0' <= char <= '5':
            self.current_input += char

    def _process_command(self, command: str):
        """Processes menu commands with functional back button"""
        # Clear input after each command
        current_input = self.current_input
        self.current_input = ""
    
        # Process back command (0 or backspace)
        if current_input in ("0", "\x08"):  # 0 or backspace
            self.current_menu_content = None
            self.showing_submenu = False
            return
    
        if self.showing_submenu:
            return  # Ignore other commands while showing a submenu
    
        # Process main commands
        self.showing_submenu = True
    
        if current_input == "1":
            self.current_menu_content = self._generate_configuration_content()
        elif current_input == "2":
            self._modify_thresholds()
            self.showing_submenu = False
        elif current_input == "3":
            self.current_menu_content = self._generate_statistics_content()
        elif current_input == "4":
            # Generate and store new summary
            self.last_summary_update = datetime.now()
            self.current_menu_content = self._generate_summary_content()
        elif current_input == "5":
            self.running = False
        else:
            self.console.print("[red]Invalid option. Use numbers 1 to 5[/]")
            self.showing_submenu = False
    
    def _generate_configuration_content(self):
        """Generates content for configuration panel with back button"""
        table = Table(title="Current Configuration", show_header=True, header_style="bold magenta")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", justify="right")
    
        for param, value in self.config.items():
            table.add_row(param.replace('_', ' ').title(), str(value))
    
        footer = Text("\n\nPress '0' to return to main menu", style="dim italic")
        return Panel(table, title="Configuration", border_style="green")
    
    def _generate_statistics_content(self):
        """Generates content for statistics with updated data"""
        table = Table(title="Statistics", show_header=True, header_style="bold magenta")
        table.add_column("Type", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Last Update", justify="right")
    
        table.add_row(
            "Total Interruptions", 
            str(self.statistics['total_interruptions']),
            self.statistics['last_update'].strftime("%H:%M:%S") if self.statistics['last_update'] else "N/A"
        )
        table.add_row(
            "Sensor Failures", 
            str(self.statistics['sensor_failure']),
            ""
        )
        table.add_row(
            "Extreme Conditions", 
            str(self.statistics['extreme_conditions']),
            ""
        )
    
        footer = Text("\n\nPress '0' to return to main menu", style="dim italic")
        return Panel(table, title="System Statistics", border_style="green")
    
    def _generate_summary_content(self):
        """Generates content for summary with updated data"""
        summary = Text()
        summary.append("📊 SYSTEM SUMMARY\n", style="bold underline blue")
        summary.append(f"Last update: {datetime.now().strftime('%H:%M:%S')}\n", style="dim")
        summary.append(f"🔄 Total interruptions: {self.statistics['total_interruptions']}\n")
        summary.append(f"⚠️  Sensor failures: {self.statistics['sensor_failure']}\n")
        summary.append(f"🚨 Extreme conditions: {self.statistics['extreme_conditions']}\n")
    
        # Add configuration information
        summary.append("\n⚙️ CURRENT CONFIGURATION\n", style="bold underline blue")
        for param, value in self.config.items():
            summary.append(f"{param.replace('_', ' ').title()}: {value}\n")
    
        # Add temporal information
        if self.statistics['last_update']:
            summary.append(f"\n⏱️ Last interruption: {self.statistics['last_update'].strftime('%H:%M:%S')}\n", style="dim")
    
        summary.append("\n\nPress '0' to return to main menu", style="dim italic")
        return Panel(summary, title="System Summary", border_style="blue")
    
    def _update_global_statistics(self):
        """Ensures statistics are updated"""
        # This method can be extended to calculate more complex statistics
        pass

    def run(self):
        """Main execution method (Windows)"""
        self.setup_layout()
        
        with Live(self.layout, refresh_per_second=10, screen=True), \
             self.run_simulation():
            
            while self.running:
                self._check_input()
                self._update_panels()
                time.sleep(0.1)