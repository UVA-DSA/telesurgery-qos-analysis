import socket
import threading
import time
import random
import struct
import json
from collections import deque
from threading import Lock, Event
import lz4.frame
import numpy as np

class PacketReorderEmulator:
    def __init__(self, input_port: int, output_port: int, 
                 params: dict,
                 protocol: str = 'udp', output_ip: str = '127.0.0.1',
                 log_packets: bool = False, log_path: str = "reorder_log.bin",
                 wait_for_full_queue: bool = False):
        """
        Initialize packet reorder emulator.
        
        Args:
            input_port (int): Port to listen for incoming packets
            output_port (int): Port to forward packets to
            params (dict): Dictionary containing emulator parameters (queue_length)
            protocol (str): Network protocol (currently only 'udp' supported)
            output_ip (str): IP address to forward packets to
            log_packets (bool): Whether to log packet reordering
            log_path (str): Path to save packet log
            wait_for_full_queue (bool): If True, only relay packets when queue is full
        """
        self.input_port = input_port
        self.output_port = output_port
        self.output_ip = output_ip
        self.protocol = protocol.lower()
        self.running = False

        # Get queue length from params with default value
        self.queue_length = params.get('queue_length', 10)

        # Packet queue and synchronization
        self.packet_queue = deque(maxlen=self.queue_length)
        self.queue_lock = Lock()
        self.queue_not_empty = Event()
        self.queue_not_full = Event()
        self.queue_not_full.set()  # Initially queue is empty, so it's not full

        # Logging setup
        self.log_packets = log_packets
        self.log_path = log_path
        self.log_queue = deque()
        self.log_lock = Lock()
        self.log_event = Event()
        self.log_thread = None

        self.wait_for_full_queue = wait_for_full_queue

    def _init_logger(self):
        """Initialize packet logging system"""
        print(f"[Logger] Starting packet writer thread for {self.log_path}")
        self.log_thread = threading.Thread(target=self._packet_writer)
        self.log_thread.daemon = True
        self.log_thread.start()

    def _log_packet(self, data: bytes, original_pos: int, new_pos: int):
        """Add packet to log queue (thread-safe)"""
        if not self.log_packets:
            return
            
        timestamp = time.time_ns()
        entry = (timestamp, len(data), original_pos, new_pos, data)
        
        with self.log_lock:
            self.log_queue.append(entry)
            self.log_event.set()

    def _packet_writer(self):
        """Dedicated thread for writing packets to disk"""
        BUFFER_SIZE = 1000
        buffer = []
        total_written = 0
        
        try:
            with open(self.log_path, "ab") as f, lz4.frame.LZ4FrameFile(f, 'wb') as compressed_file:
                while self.running or buffer:
                    self.log_event.wait(timeout=1)
                    
                    with self.log_lock:
                        while self.log_queue:
                            buffer.append(self.log_queue.popleft())
                        self.log_event.clear()

                    if len(buffer) >= BUFFER_SIZE or not self.running:
                        binary_data = b''.join(
                            struct.pack(
                                "!QHii%ds" % length,
                                ts, length, orig_pos, new_pos, data
                            ) for ts, length, orig_pos, new_pos, data in buffer
                        )
                        compressed_file.write(binary_data)
                        compressed_file.flush()
                        total_written += len(buffer)
                        buffer.clear()
                        
        except Exception as e:
            print(f"[Writer] Critical error: {str(e)}")
            raise

    def _forward_packets(self):
        """Forward packets from queue in random order"""
        forward_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        packet_counter = 0

        while self.running:
            if self.wait_for_full_queue:
                # Wait until queue is full before processing
                while self.running and len(self.packet_queue) < self.queue_length:
                    time.sleep(0.001)
                if not self.running:
                    break
            else:
                # Original behavior - wait for any packets
                self.queue_not_empty.wait(timeout=0.1)

            with self.queue_lock:
                if len(self.packet_queue) > 0 and (not self.wait_for_full_queue or len(self.packet_queue) == self.queue_length):
                    # Randomly select a packet from queue
                    idx = random.randrange(len(self.packet_queue))
                    data, seq = self.packet_queue[idx]
                    self.packet_queue[idx] = self.packet_queue[-1]
                    self.packet_queue.pop()

                    if len(self.packet_queue) < self.queue_length:
                        self.queue_not_full.set()
                    
                    if len(self.packet_queue) == 0:
                        self.queue_not_empty.clear()
                else:
                    continue

            # Log reordering if enabled
            if self.log_packets:
                self._log_packet(data, seq, packet_counter)
            
            # Forward the packet
            forward_sock.sendto(data, (self.output_ip, self.output_port))
            packet_counter += 1
        
        forward_sock.close()

    def _udp_listener(self):
        """Handle UDP packet reordering"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', self.input_port))
        packet_counter = 0
        
        while self.running:
            data, addr = sock.recvfrom(4096)
            
            self.queue_not_full.wait()  # Wait if queue is full
            
            with self.queue_lock:
                self.packet_queue.append((data, packet_counter))
                packet_counter += 1
                
                if len(self.packet_queue) == self.queue_length:
                    self.queue_not_full.clear()
                
                if len(self.packet_queue) == 1:  # First packet in queue
                    self.queue_not_empty.set()
        
        sock.close()

    def start(self):
        """Start the reorder emulator"""
        self.running = True
        if self.log_packets:
            self._init_logger()
        
        if self.protocol == 'udp':
            # Start packet forwarder thread
            self.forward_thread = threading.Thread(target=self._forward_packets)
            self.forward_thread.daemon = True
            self.forward_thread.start()
            
            # Start listener thread
            self.thread = threading.Thread(target=self._udp_listener)
            self.thread.daemon = True
            self.thread.start()
        else:
            raise ValueError("Invalid protocol. Use 'udp'")

    def stop(self):
        """Stop the reorder emulator"""
        self.running = False
        
        if self.thread:
            print("[Network] Stopping threads...")
            self.log_event.set()
            self.queue_not_empty.set()
            self.queue_not_full.set()
            
            if self.log_thread:
                self.log_thread.join(timeout=2)
                if self.log_thread.is_alive():
                    print("[Network] WARNING: Logger thread did not terminate cleanly")
                else:
                    print("[Network] Logger thread stopped successfully")
            
            if self.forward_thread:
                self.forward_thread.join(timeout=2)
            self.thread.join(timeout=1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Network packet reorder emulator')
    parser.add_argument('--input-port', type=int, required=True,
                      help='Port to listen for incoming packets')
    parser.add_argument('--output-port', type=int, required=True, 
                      help='Port to forward packets to')
    parser.add_argument('--output-ip', default='127.0.0.1',
                      help='IP address to forward packets to (default: 127.0.0.1)')
    parser.add_argument('--protocol', choices=['udp'], default='udp',
                      help='Network protocol (default: udp)')
    parser.add_argument('--params-path', required=True,
                      help='Path to config file with queue_length parameter')
    parser.add_argument('--log', help='Path to packet log file (optional)')
    parser.add_argument('--wait-for-full', action='store_true',
                      help='Only relay packets when queue is full')

    args = parser.parse_args()

    def signal_handler(signum, frame):
        emulator.stop()
        sys.exit(0)

    import signal
    import sys
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    emulator = PacketReorderEmulator(
        input_port=args.input_port,
        output_port=args.output_port,
        output_ip=args.output_ip,
        params_path=args.params_path,
        protocol=args.protocol,
        log_packets=bool(args.log),
        log_path=args.log if args.log else "reorder_log.bin",
        wait_for_full_queue=args.wait_for_full
    )

    try:
        emulator.start()
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"Error: {e}")
        signal_handler(None, None)
