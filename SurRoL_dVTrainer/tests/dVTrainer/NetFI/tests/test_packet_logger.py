import threading
import time
from netfi.emulators import PacketLoggerEmulator
import socket
import struct
import lz4.frame

def packet_sender(host, port, num_packets):
    """Send test packets"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for i in range(num_packets):
        # Create packet with sequence number
        data = struct.pack('!I', i)
        sock.sendto(data, (host, port))
        time.sleep(0.001)  # Small delay between packets
    sock.close()

def packet_receiver(port, num_packets):
    """Receive and count packets"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', port))
    received = 0
    
    while received < num_packets:
        data, addr = sock.recvfrom(1024)
        received += 1
        
    sock.close()
    print(f"[Receiver] Received {received} packets")

def analyze_log(log_file: str) -> dict:
    """
    Analyze the packet log to verify all packets were properly logged.
    
    Args:
        log_file: Path to the log file
    
    Returns:
        dict: Statistics about the logged packets
    """
    stats = {
        'total_packets': 0,
        'unique_packets': set(),
        'duplicate_packets': [],
        'missing_packets': [],
        'out_of_order': 0,
        'first_seq': None,
        'last_seq': None
    }
    
    print(f"[Analyzer] Reading log file: {log_file}")
    
    try:
        with lz4.frame.open(log_file, 'rb') as f:
            last_seq = -1
            while True:
                # Read packet header
                header = f.read(11)  # 8 (timestamp) + 2 (length) + 1 (dropped flag)
                if not header:
                    break
                    
                ts, length, dropped = struct.unpack("!QH?", header)
                data = f.read(length)
                
                # Extract sequence number from packet data
                seq = struct.unpack('!I', data[:4])[0]
                
                # Track first and last sequence numbers
                if stats['first_seq'] is None:
                    stats['first_seq'] = seq
                stats['last_seq'] = seq
                
                # Check for out-of-order packets
                if seq < last_seq:
                    stats['out_of_order'] += 1
                last_seq = seq
                
                # Track unique and duplicate packets
                if seq in stats['unique_packets']:
                    stats['duplicate_packets'].append(seq)
                else:
                    stats['unique_packets'].add(seq)
                
                stats['total_packets'] += 1
                
            # Find missing packets in the sequence
            expected_range = set(range(stats['first_seq'], stats['last_seq'] + 1))
            stats['missing_packets'] = sorted(expected_range - stats['unique_packets'])
            
    except FileNotFoundError:
        print(f"[Error] Log file not found: {log_file}")
        return stats
    except Exception as e:
        print(f"[Error] Failed to analyze log: {str(e)}")
        return stats
    
    # Print analysis results
    print("\n=== Packet Log Analysis ===")
    print(f"Total packets logged: {stats['total_packets']}")
    print(f"Unique packets: {len(stats['unique_packets'])}")
    print(f"Sequence range: {stats['first_seq']} to {stats['last_seq']}")
    print(f"Out of order packets: {stats['out_of_order']}")
    
    if stats['duplicate_packets']:
        print(f"Duplicate packets: {len(stats['duplicate_packets'])}")
        print(f"First few duplicates: {stats['duplicate_packets'][:5]}")
    
    if stats['missing_packets']:
        print(f"Missing packets: {len(stats['missing_packets'])}")
        print(f"First few missing: {stats['missing_packets'][:5]}")
    else:
        print("No missing packets - all sequences logged successfully!")
    
    return stats

if __name__ == "__main__":
    # Configuration
    LOGGER_PORT = 5000
    RECEIVER_PORT = 5001
    NUM_PACKETS = 1000
    LOG_FILE = "packet_relay.bin"
    
    # Start Packet Logger
    print("[Main] Starting packet logger...")
    logger = PacketLoggerEmulator(
        input_port=LOGGER_PORT,
        output_port=RECEIVER_PORT,
        protocol='udp',
        log_path=LOG_FILE
    )
    
    # Start receiver first
    print("[Main] Starting receiver thread...")
    receiver_thread = threading.Thread(
        target=packet_receiver, 
        args=(RECEIVER_PORT, NUM_PACKETS)
    )
    receiver_thread.start()
    
    # Start logger
    print("[Main] Starting logger...")
    logger.start()
    time.sleep(1)  # Wait for logger to initialize
    
    # Start sender
    print("[Main] Starting sender thread...")
    sender_thread = threading.Thread(
        target=packet_sender,
        args=('localhost', LOGGER_PORT, NUM_PACKETS)
    )
    sender_thread.start()
    
    # Wait for completion
    sender_thread.join()
    print("[Main] Sender thread completed")
    receiver_thread.join()
    print("[Main] Receiver thread completed")
    
    # Stop logger
    print("[Main] Stopping logger...")
    logger.stop()
    print("[Main] Logger stopped")
    
    # Analyze the log file
    print("\n[Main] Analyzing log file...")
    stats = analyze_log(LOG_FILE)
    
    # Verify all packets were logged
    if len(stats['missing_packets']) == 0 and len(stats['duplicate_packets']) == 0:
        print("\n[Success] All packets were properly logged!")
    else:
        print("\n[Warning] Some packets were missing or duplicated!") 