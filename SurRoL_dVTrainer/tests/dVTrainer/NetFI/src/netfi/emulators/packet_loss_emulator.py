import os
import socket
import threading
import time
import json
from netfi.models import GEClassicModel, GEParetoBLLModel, RandomLossModel, CommunicationLossModel
import signal
import sys
import struct
from collections import deque
from threading import Lock, Event
import lz4.frame


class PacketLossEmulator:
    def __init__(self, input_port: int, output_port: int, 
                 model_name: str, params: dict, 
                 protocol: str = 'udp', output_ip: str = '127.0.0.1',
                 log_packets: bool = False, log_path: str = "packet_log.bin"):
        """
        Initialize packet loss emulator.
        
        Args:
            input_port (int): Port to listen for incoming packets
            output_port (int): Port to forward packets to
            model_name (str): Name of the loss model (GE_Classic or GE_Pareto_BLL)
            params (dict): Dictionary containing model parameters
            protocol (str): Network protocol (currently only 'udp' supported)
            output_ip (str): IP address to forward packets to
            log_packets (bool): Whether to log packet losses
            log_path (str): Path to save packet log
        """
        self.input_port = input_port
        self.output_port = output_port
        self.output_ip = output_ip
        self.protocol = protocol.lower()
        self.running = False
        self.loss_model = self._init_loss_model(model_name, params)

        self.log_packets = log_packets
        self.log_path = log_path
        self.log_queue = deque()
        self.log_lock = Lock()
        self.log_event = Event()
        self.log_thread = None

    def _init_loss_model(self, model_name: str, params: dict):
        """Initialize the packet loss model from parameters"""
        if model_name.lower() == 'GE_Classic'.lower():
            model_params = params['GE_Classic']
            return GEClassicModel(model_params)
        elif model_name.lower() == 'GE_Pareto_BLL'.lower():
            model_params = params['GE_Pareto_BLL']
            return GEParetoBLLModel(model_params)
        elif model_name.lower() == 'Random_Loss'.lower():
            model_params = params['Random_Loss']
            return RandomLossModel(model_params)
        elif model_name.lower() == 'Communication_Loss'.lower():
            model_params = params['Communication_Loss']['params']
            return CommunicationLossModel(model_params)
        else:
            raise ValueError(f"Unknown model: {model_name}")


    def _init_logger(self):
        """Initialize packet logging system"""
        print(f"[Logger] Starting packet writer thread for {self.log_path}")
        # Remove existing log file if it exists
        if os.path.exists(self.log_path):
            try:
                os.remove(self.log_path)
                print(f"[Logger] Removed existing log file: {self.log_path}")
            except OSError as e:
                print(f"[Logger] Error removing existing log file: {e}")
        self.log_thread = threading.Thread(target=self._packet_writer)
        self.log_thread.daemon = True
        self.log_thread.start()

    def _log_packet(self, data: bytes, dropped: bool):
        """Add packet to log queue (thread-safe)"""
        if not self.log_packets:
            return
            
        timestamp = time.time_ns()
        entry = (timestamp, len(data), dropped, data)
        
        with self.log_lock:
            self.log_queue.append(entry)
            self.log_event.set()
            # Debug print every 100 packets
            if len(self.log_queue) % 100 == 0:
                print(f"[Logger] Queue size: {len(self.log_queue)} packets")

    def _packet_writer(self):
        """Dedicated thread for writing packets to disk"""
        BUFFER_SIZE = 1000
        buffer = []
        total_written = 0
        print(f"[Writer] Starting with buffer size {BUFFER_SIZE}")
        
        try:
            with open(self.log_path, "ab") as f, lz4.frame.LZ4FrameFile(f, 'wb') as compressed_file:
                print(f"[Writer] Opened log file: {self.log_path}")
                
                while self.running or buffer:
                    self.log_event.wait(timeout=1)
                    
                    # Collect data from queue
                    with self.log_lock:
                        qsize = len(self.log_queue)
                        if qsize > 0:
                            while self.log_queue:
                                buffer.append(self.log_queue.popleft())
                            self.log_event.clear()

                    # Write when buffer reaches threshold
                    if len(buffer) >= BUFFER_SIZE or not self.running:
                        write_time = time.time()
                        batch_size = len(buffer)
                        binary_data = b''.join(
                            struct.pack(
                                "!QH?%ds" % length,
                                ts, length, dropped, data
                            ) for ts, length, dropped, data in buffer
                        )
                        
                        compressed_file.write(binary_data)
                        compressed_file.flush()
                        total_written += batch_size
                        print(f"[Writer] Wrote {batch_size} packets ({len(binary_data)//1024}KB) "
                              f"in {(time.time()-write_time)*1000:.1f}ms "
                              f"(Total: {total_written})")
                        buffer.clear()
                        
                print(f"[Writer] Final flush completed. Total packets written: {total_written}")
                
        except Exception as e:
            print(f"[Writer] Critical error: {str(e)}")
            raise

    def _udp_listener(self):
        """Handle UDP packet loss simulation"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', self.input_port))
        
        forward_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        while self.running:
            data, addr = sock.recvfrom(4096)
            drop = self.loss_model.should_drop()
            
            if self.log_packets:
                self._log_packet(data, drop)
                
            if not drop:
                forward_sock.sendto(data, (self.output_ip, self.output_port))
        
        forward_sock.close()
        sock.close()


    def start(self):
        """Start the network emulator"""
        self.running = True
        if self.log_packets:
            self._init_logger()
        
        if self.protocol == 'udp':
            self.thread = threading.Thread(target=self._udp_listener)
            self.thread.daemon = True  # Make thread a daemon
            self.thread.start()
        else:
            raise ValueError("Invalid protocol. Use 'udp'")

    def stop(self):
        """Stop the network emulator"""
        self.running = False

        if self.thread:
            print("[Network] Stopping logger thread...")
            self.log_event.set()
            if self.log_thread:
                self.log_thread.join(timeout=2)
                if self.log_thread.is_alive():
                    print("[Network] WARNING: Logger thread did not terminate cleanly")
                else:
                    print("[Network] Logger thread stopped successfully")
            self.thread.join(timeout=1)

    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        self.stop()
        sys.exit(0)

# Example usage:
if __name__ == "__main__":
    import argparse

    # Set up argument parser
    parser = argparse.ArgumentParser(description='Network packet loss emulator')
    parser.add_argument('--input-port', type=int, required=True,
                      help='Port to listen for incoming packets')
    parser.add_argument('--output-port', type=int, required=True, 
                      help='Port to forward packets to')
    parser.add_argument('--output-ip', default='127.0.0.1',
                      help='IP address to forward packets to (default: 127.0.0.1)')
    parser.add_argument('--protocol', choices=['udp'], required=True,
                      help='Network protocol (udp)')
    parser.add_argument('--model', choices=['GE_Classic', 'GE_Pareto_BLL'], required=True,
                      help='Packet loss model to use')
    parser.add_argument('--config', required=True,
                      help='Path to model parameters config file')
    parser.add_argument('--log', help='Path to packet log file (optional)')

    args = parser.parse_args()

    # Set up signal handler
    def signal_handler(signum, frame):
        emulator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and start emulator
    emulator = PacketLossEmulator(
        input_port=args.input_port,
        output_port=args.output_port,
        output_ip=args.output_ip,
        model_name=args.model,
        params=json.load(open(args.config)),

        protocol=args.protocol,
        log_packets=bool(args.log),
        log_path=args.log if args.log else "packet_log.bin"
    )

    try:
        emulator.start()
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"Error: {e}")
        signal_handler(None, None)
