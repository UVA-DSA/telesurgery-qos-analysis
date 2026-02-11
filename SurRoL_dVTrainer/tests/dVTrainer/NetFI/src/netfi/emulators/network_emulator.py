import socket
import json
import time
import os
from typing import List, Dict, Any
from pathlib import Path

class NetworkEmulator:
    """Composite network emulator that chains multiple emulators together"""
    
    def __init__(self, 
                 pipeline: List[Any],
                 master_config: dict,
                 input_port: int,
                 output_port: int,
                 output_ip: str,
                 log_path: str = None):
        """
        Initialize network emulator pipeline
        
        Args:
            pipeline: List of emulator classes to chain together
            master_config: Configuration for all emulators
            input_port: Port to receive incoming packets
            output_port: Port to send outgoing packets
            output_ip: IP to send outgoing packets
            log_path: Directory path to store emulator logs
        """
        self.pipeline = pipeline
        self.master_config = master_config
        self.input_port = input_port
        self.output_port = output_port
        self.output_ip = output_ip
        
        # Set up logging directory
        self.log_path = None
        if log_path:
            self.log_path = Path(log_path)
            self.log_path.mkdir(parents=True, exist_ok=True)
            
        # Initialize emulator chain
        self.emulators = []
        self._setup_pipeline()
        
    def _setup_pipeline(self):
        """Create and connect emulators in the pipeline"""
        num_emulators = len(self.pipeline)
        
        # Generate unique ports for inter-emulator connections
        ports = self._generate_port_sequence(num_emulators + 1)
        
        # Configure each emulator with appropriate ports
        for i, EmulatorClass in enumerate(self.pipeline):
            # Extract config for this emulator type
            config = self.master_config.get(EmulatorClass.__name__, {})
            
            # Set up logging for this emulator if logging is enabled
            log_config = {}
            if self.log_path:
                emulator_name = EmulatorClass.__name__.lower()
                log_filename = f"{emulator_name}_{i+1}.bin"
                log_file = self.log_path / log_filename
                log_config = {
                    'log_packets': True,
                    'log_path': str(log_file)
                }
            
            # Create emulator instance
            emulator = EmulatorClass(
                input_port=self.input_port if i == 0 else ports[i],
                output_port=ports[i+1] if i < num_emulators-1 else self.output_port,
                output_ip=self.output_ip if i == num_emulators-1 else '127.0.0.1',
                **config,
                **log_config
            )
            
            self.emulators.append(emulator)
            
    def _generate_port_sequence(self, count: int) -> List[int]:
        """Generate port sequence starting with input_port, ending with output_port"""
        base_port = self.input_port + 1
        return [base_port + i for i in range(count)]
            
    def start(self):
        """Start the emulator pipeline"""
        # Start all emulators
        for emulator in self.emulators:
            emulator.start()
        
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """Stop all emulators in the pipeline"""
        for emulator in self.emulators:
            emulator.stop()
