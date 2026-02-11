import socket
import threading
import time
import json
import signal
import sys
from collections import deque
from threading import Lock, Event
import struct
import lz4.frame
import heapq

from netfi.models import DelayModel


class DelayEmulator:
    def __init__(self, input_port: int, output_port: int,
                 params: dict, network_type: str = '4G',
                 protocol: str = 'udp', output_ip: str = '127.0.0.1',
                 log_packets: bool = False, log_path: str = "delay_log.bin"):
        """
        Initialize delay emulator.
        
        Args:
            input_port (int): Port to listen for incoming packets
            output_port (int): Port to forward packets to
            params (dict): Dictionary containing delay model parameters
            network_type (str): Network type (4G, 5G, etc.)
            protocol (str): Network protocol (currently only 'udp' supported)
            output_ip (str): IP address to forward packets to
            log_packets (bool): Whether to log packet delays
            log_path (str): Path to save packet log
        """
        self.input_port = input_port
        self.output_port = output_port
        self.output_ip = output_ip
        self.protocol = protocol.lower()
        self.running = False
        
        # Initialize delay model from params
        model_params = params[network_type]
        self.delay_model = DelayModel(
            lower_bound=model_params['lower_bound'],
            weights=model_params['weights'],
            lambdas=model_params['lambdas']
        )

        # Priority queue for delayed packets [(scheduled_time, data), ...]
        self.packet_queue = []
        self.queue_lock = Lock()

        # Logging setup
        self.log_packets = log_packets
        self.log_path = log_path
        self.log_queue = deque()
        self.log_lock = Lock()
        self.log_event = Event()
        self.log_thread = None
        self.forward_thread = None

    def _init_logger(self):
        """Initialize packet logging system"""
        print(f"[Logger] Starting packet writer thread for {self.log_path}")
        self.log_thread = threading.Thread(target=self._packet_writer)
        self.log_thread.daemon = True
        self.log_thread.start()

    def _log_packet(self, data: bytes, delay: float):
        """Add packet to log queue (thread-safe)"""
        if not self.log_packets:
            return

        timestamp = time.time_ns()
        entry = (timestamp, len(data), delay, data)

        with self.log_lock:
            self.log_queue.append(entry)
            self.log_event.set()
            if len(self.log_queue) % 100 == 0:
                print(f"[Logger] Queue size: {len(self.log_queue)} packets")

    def _packet_writer(self):
        """Dedicated thread for writing packets to disk"""
        BUFFER_SIZE = 1000
        buffer = []
        total_written = 0

        try:
            with open(self.log_path, "ab") as f, lz4.frame.LZ4FrameFile(f, 'wb') as compressed_file:
                print(f"[Writer] Opened log file: {self.log_path}")

                while self.running or buffer:
                    self.log_event.wait(timeout=1)

                    with self.log_lock:
                        while self.log_queue:
                            buffer.append(self.log_queue.popleft())
                        self.log_event.clear()

                    if len(buffer) >= BUFFER_SIZE or not self.running:
                        write_time = time.time()
                        batch_size = len(buffer)
                        binary_data = b''.join(
                            struct.pack(
                                "!QHf%ds" % length,
                                ts, length, delay, data
                            ) for ts, length, delay, data in buffer
                        )

                        compressed_file.write(binary_data)
                        compressed_file.flush()
                        total_written += batch_size
                        print(f"[Writer] Wrote {batch_size} packets ({len(binary_data)//1024}KB) "
                              f"in {(time.time()-write_time)*1000:.1f}ms "
                              f"(Total: {total_written})")
                        buffer.clear()

        except Exception as e:
            print(f"[Writer] Critical error: {str(e)}")
            raise

    def _forward_packets(self):
        """Forward delayed packets when their time has come"""
        forward_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        while self.running:
            current_time = time.time()

            with self.queue_lock:
                while self.packet_queue and self.packet_queue[0][0] <= current_time:
                    _, data = heapq.heappop(self.packet_queue)
                    forward_sock.sendto(
                        data, (self.output_ip, self.output_port))

            time.sleep(0.001)  # Small sleep to prevent CPU hogging

        forward_sock.close()

    def _udp_listener(self):
        """Handle UDP packet delay simulation"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', self.input_port))

        while self.running:
            data, addr = sock.recvfrom(4096)
            delay = self.delay_model.sample_delay() / 1000.0  # Convert ms to seconds
            scheduled_time = time.time() + delay

            if self.log_packets:
                self._log_packet(data, delay)

            with self.queue_lock:
                heapq.heappush(self.packet_queue, (scheduled_time, data))

        sock.close()

    def start(self):
        """Start the delay emulator"""
        self.running = True
        if self.log_packets:
            self._init_logger()

        if self.protocol == 'udp':
            # Start packet forwarder thread
            self.forward_thread = threading.Thread(
                target=self._forward_packets)
            self.forward_thread.daemon = True
            self.forward_thread.start()

            # Start listener thread
            self.thread = threading.Thread(target=self._udp_listener)
            self.thread.daemon = True
            self.thread.start()
        else:
            raise ValueError("Invalid protocol. Use 'udp'")

    def stop(self):
        """Stop the delay emulator"""
        self.running = False

        if self.thread:
            print("[Network] Stopping threads...")
            self.log_event.set()
            if self.log_thread:
                self.log_thread.join(timeout=2)
                if self.log_thread.is_alive():
                    print(
                        "[Network] WARNING: Logger thread did not terminate cleanly")
                else:
                    print("[Network] Logger thread stopped successfully")

            if self.forward_thread:
                self.forward_thread.join(timeout=2)
            self.thread.join(timeout=1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Network delay emulator')
    parser.add_argument('--input-port', type=int, required=True,
                        help='Port to listen for incoming packets')
    parser.add_argument('--output-port', type=int, required=True,
                        help='Port to forward packets to')
    parser.add_argument('--output-ip', default='127.0.0.1',
                        help='IP address to forward packets to (default: 127.0.0.1)')
    parser.add_argument('--protocol', choices=['udp'], default='udp',
                        help='Network protocol (default: udp)')
    parser.add_argument('--network-type', choices=['4G', '5G'], default='4G',
                        help='Network type to emulate (default: 4G)')
    parser.add_argument('--config', required=True,
                        help='Path to delay model parameters config file')
    parser.add_argument('--log', help='Path to packet log file (optional)')

    args = parser.parse_args()

    def signal_handler(signum, frame):
        emulator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    emulator = DelayEmulator(
        input_port=args.input_port,
        output_port=args.output_port,
        output_ip=args.output_ip,
        network_type=args.network_type,
        params=json.load(open(args.config)),
        protocol=args.protocol,
        log_packets=bool(args.log),
        log_path=args.log if args.log else "delay_log.bin"
    )

    try:
        emulator.start()
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"Error: {e}")
        signal_handler(None, None)
