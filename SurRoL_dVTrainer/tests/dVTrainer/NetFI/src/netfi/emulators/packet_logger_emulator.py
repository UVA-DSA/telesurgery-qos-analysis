import socket
import threading
import time
import struct
from collections import deque
from threading import Lock, Event
import lz4.frame

class PacketLoggerEmulator:
    def __init__(self, input_port: int, output_port: int, 
                 protocol: str = 'udp', output_ip: str = '127.0.0.1',
                 log_path: str = "packet_log.bin"):
        """
        Initialize packet logger that relays and logs all packets.
        
        Args:
            input_port (int): Port to listen for incoming packets
            output_port (int): Port to forward packets to
            protocol (str): Network protocol (currently only 'udp' supported)
            output_ip (str): IP address to forward packets to
            log_path (str): Path to save packet log
        """
        self.input_port = input_port
        self.output_port = output_port
        self.output_ip = output_ip
        self.protocol = protocol.lower()
        self.running = False
        
        # Logging setup
        self.log_path = log_path
        self.log_queue = deque()
        self.log_lock = Lock()
        self.log_event = Event()

    def _init_sockets(self):
        """Initialize UDP sockets for input and output"""
        if self.protocol == 'udp':
            self.input_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.output_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.input_socket.bind(('0.0.0.0', self.input_port))
        else:
            raise ValueError(f"Unsupported protocol: {self.protocol}")

    def _packet_writer(self):
        """Write logged packets to compressed binary file"""
        with lz4.frame.open(self.log_path, 'wb') as f:
            while self.running or len(self.log_queue) > 0:
                # Wait for new packets or check every second
                self.log_event.wait(timeout=1.0)
                self.log_event.clear()
                
                # Write any queued packets
                while len(self.log_queue) > 0:
                    with self.log_lock:
                        timestamp, length, dropped, data = self.log_queue.popleft()
                    
                    # Write packet header: timestamp (8 bytes), length (2 bytes), dropped flag (1 byte)
                    header = struct.pack("!QH?", timestamp, length, dropped)
                    f.write(header)
                    
                    # Write packet data
                    f.write(struct.pack(f"!{length}s", data))

    def _process_packets(self):
        """Main packet processing loop"""
        while self.running:
            try:
                data, addr = self.input_socket.recvfrom(65535)
                
                # Log the packet
                timestamp = time.time_ns()
                entry = (timestamp, len(data), False, data)
                
                with self.log_lock:
                    self.log_queue.append(entry)
                    self.log_event.set()

                # Forward the packet
                self.output_socket.sendto(data, (self.output_ip, self.output_port))
                
            except socket.error as e:
                if self.running:  # Only log errors if we're still supposed to be running
                    print(f"Socket error: {e}")

    def start(self):
        """Start the packet logger"""
        print(f"[PacketLogger] Starting on port {self.input_port}")
        self.running = True
        self._init_sockets()
        
        # Start packet writer thread
        self.writer_thread = threading.Thread(target=self._packet_writer)
        self.writer_thread.daemon = True
        self.writer_thread.start()
        
        # Start packet processing thread
        self.process_thread = threading.Thread(target=self._process_packets)
        self.process_thread.daemon = True
        self.process_thread.start()

    def stop(self):
        """Stop the packet logger"""
        print("[PacketLogger] Stopping...")
        self.running = False
        
        # Close sockets
        if hasattr(self, 'input_socket'):
            self.input_socket.close()
        if hasattr(self, 'output_socket'):
            self.output_socket.close()
        
        # Wait for threads to finish
        if hasattr(self, 'process_thread'):
            self.process_thread.join()
        if hasattr(self, 'writer_thread'):
            self.log_event.set()  # Wake up writer thread
            self.writer_thread.join()
        
        print("[PacketLogger] Stopped")
