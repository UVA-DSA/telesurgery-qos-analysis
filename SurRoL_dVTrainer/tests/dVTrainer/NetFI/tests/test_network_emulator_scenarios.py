import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from netfi.emulators import NetworkEmulator, DelayEmulator, PacketLossEmulator, PacketReorderEmulator
import threading
import time
import socket
import struct
import random
import string
import json
import argparse
import lz4.frame
from pathlib import Path

from test_utils import ThreadWithReturn


def generate_random_payload(length=32):
    """Generate random string payload"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length)).encode()

def packet_sender(host: str, port: int, num_packets: int):
    """Send UDP packets with sequence numbers and timestamps"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[Sender] Starting to send {num_packets} packets...")
    start_time = time.time()
    
    for i in range(num_packets):
        timestamp = time.time_ns()
        payload = generate_random_payload()
        data = struct.pack(f'!IQ{len(payload)}s', i, timestamp, payload)
        sock.sendto(data, (host, port))
        
        if i % 1000 == 0 and i > 0:
            print(f"[Sender] Sent {i}/{num_packets} packets ({i/num_packets:.0%})")
    
    sock.close()
    duration = time.time() - start_time
    print(f"[Sender] Completed in {duration:.2f}s ({num_packets/duration:.0f} pkt/s)")

def packet_receiver(port: int, num_packets: int):
    """Receive UDP packets and track metrics"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', port))
    sock.settimeout(5)
    
    packet_data = {
        'delays': {},      # {seq: delay_ms}
        'received': set(), # set of received sequence numbers
        'order': {},      # {seq: receive_order}
    }
    
    receive_counter = 0
    print(f"[Receiver] Listening on port {port} for {num_packets} packets...")
    start_time = time.time()
    last_print = 0
    last_received = 0
    timeout_counter = 0
    
    while len(packet_data['received']) < num_packets and timeout_counter < 3:
        try:
            data, _ = sock.recvfrom(4096)
            receive_time = time.time_ns()
            
            seq, send_time = struct.unpack('!IQ', data[:12])
            delay_ms = (receive_time - send_time) / 1_000_000
            
            packet_data['delays'][seq] = delay_ms
            packet_data['received'].add(seq)
            packet_data['order'][seq] = receive_counter
            receive_counter += 1
            
            last_received = time.time()
            timeout_counter = 0
            
            if time.time() - last_print > 2:
                print(f"[Receiver] Received {len(packet_data['received'])}/{num_packets} "
                      f"packets ({len(packet_data['received'])/num_packets:.0%})")
                last_print = time.time()
        
        except socket.timeout:
            if time.time() - last_received > 10:
                timeout_counter += 1
                print(f"[Receiver] Timeout {timeout_counter}/3 - No packets received for 10 seconds")
            continue
    
    sock.close()
    duration = time.time() - start_time
    print(f"[Receiver] Completed in {duration:.2f}s ({len(packet_data['received'])/duration:.0f} pkt/s)")
    return packet_data

def analyze_results(packet_data, num_packets):
    """Analyze packet metrics"""
    stats = {
        'total_sent': num_packets,
        'total_received': len(packet_data['received']),
        'loss_rate': 1 - len(packet_data['received']) / num_packets,
    }
    
    if packet_data['delays']:
        delays = list(packet_data['delays'].values())
        stats.update({
            'min_delay': min(delays),
            'max_delay': max(delays),
            'mean_delay': np.mean(delays),
            'median_delay': np.median(delays),
            'std_delay': np.std(delays),
            'p95_delay': np.percentile(delays, 95),
            'p99_delay': np.percentile(delays, 99),
        })
    
    if packet_data['order']:
        reorder_numbers = []
        for seq in range(num_packets):
            if seq in packet_data['order']:
                reorder_number = abs(seq - packet_data['order'][seq])
                reorder_numbers.append(reorder_number)
        
        if reorder_numbers:
            stats.update({
                'max_reorder': max(reorder_numbers),
                'mean_reorder': np.mean(reorder_numbers),
                'median_reorder': np.median(reorder_numbers),
                'std_reorder': np.std(reorder_numbers),
                'p95_reorder': np.percentile(reorder_numbers, 95),
                'ordered_packets': sum(1 for r in reorder_numbers if r == 0),
            })
    
    return stats

def visualize_scenario(stats, scenario_name):
    """Create visualization for scenario results"""
    plt.style.use('ggplot')
    fig = plt.figure(figsize=(20, 10))
    
    # Create grid layout based on metrics present
    has_delay = 'mean_delay' in stats
    has_loss = 'loss_rate' in stats
    has_reorder = 'mean_reorder' in stats
    
    num_plots = sum([has_delay, has_loss, has_reorder])
    gs = fig.add_gridspec(2, num_plots + 1, width_ratios=[1] * num_plots + [0.5])
    
    plot_idx = 0
    
    # Delay plots
    if has_delay:
        ax = fig.add_subplot(gs[0, plot_idx])
        delays = list(stats['delays'].values())
        sns.histplot(data=delays, bins=50, ax=ax,
                    color='#2e86de', edgecolor='#1a3c6d')
        ax.set_title('Delay Distribution', fontsize=14)
        ax.set_xlabel('Delay (ms)')
        plot_idx += 1
    
    # Loss visualization
    if has_loss:
        ax = fig.add_subplot(gs[0, plot_idx])
        received = np.zeros(stats['total_sent'])
        received[list(stats['received'])] = 1
        ax.plot(received, 'b.', markersize=1)
        ax.set_title('Packet Loss Pattern', fontsize=14)
        ax.set_xlabel('Packet Sequence')
        ax.set_ylabel('Received (1) / Lost (0)')
        plot_idx += 1
    
    # Reorder visualization
    if has_reorder:
        ax = fig.add_subplot(gs[0, plot_idx])
        reorder_numbers = []
        for seq in range(stats['total_sent']):
            if seq in stats['order']:
                reorder_number = abs(seq - stats['order'][seq])
                reorder_numbers.append(reorder_number)
        sns.histplot(data=reorder_numbers, bins=50, ax=ax,
                    color='#2e86de', edgecolor='#1a3c6d')
        ax.set_title('Reorder Number Distribution', fontsize=14)
        ax.set_xlabel('Reorder Number')
        
    # Statistics Panel
    ax_stats = fig.add_subplot(gs[:, -1])
    ax_stats.axis('off')
    
    stats_text = [
        f"Scenario: {scenario_name}",
        "─" * 25,
        f"Total Packets: {stats['total_sent']:,}",
        f"Received Packets: {stats['total_received']:,}",
    ]
    
    if has_loss:
        stats_text.extend([
            f"Loss Rate: {stats['loss_rate']:.2%}",
        ])
    
    if has_delay:
        stats_text.extend([
            f"Min Delay: {stats['min_delay']:.2f} ms",
            f"Max Delay: {stats['max_delay']:.2f} ms",
            f"Mean Delay: {stats['mean_delay']:.2f} ms",
            f"Std Dev Delay: {stats['std_delay']:.2f} ms",
        ])
    
    if has_reorder:
        stats_text.extend([
            f"Max Reorder: {stats['max_reorder']:.0f}",
            f"Mean Reorder: {stats['mean_reorder']:.2f}",
            f"Ordered Packets: {stats['ordered_packets']:,}",
            f"Ordered Ratio: {stats['ordered_packets']/stats['total_received']:.1%}",
        ])
    
    ax_stats.text(0.1, 0.7, "\n".join(stats_text),
                fontsize=12, linespacing=1.8,
                color='#2d3436', fontfamily='monospace',
                bbox=dict(facecolor='#f8f9fa', edgecolor='#dfe6e9',
                        boxstyle='round,pad=1'))
    
    plt.suptitle(f"Network Emulation Analysis - {scenario_name}",
                fontsize=18, y=0.98,
                color='#2d3436', fontweight='bold')
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()

def analyze_emulator_logs(log_dir: str, scenario_config: list):
    """Analyze logs from all emulators in the scenario"""
    stats = {}
    log_dir = Path(log_dir)
    
    for i, emulator in enumerate(scenario_config):
        emulator_type = emulator['type']
        log_file = log_dir / f"{emulator_type}emulator_{i+1}.bin"
        
        if emulator_type == 'delay':
            delay_stats = analyze_delay_log(log_file)
            stats.update(delay_stats)
        elif emulator_type == 'loss':
            loss_stats = analyze_loss_log(log_file)
            stats.update(loss_stats)
        elif emulator_type == 'reorder':
            reorder_stats = analyze_reorder_log(log_file)
            stats.update(reorder_stats)
    
    return stats

def analyze_delay_log(log_file: Path):
    """Analyze delay emulator log file"""
    delays = []
    with open(log_file, 'rb') as f:
        with lz4.frame.LZ4FrameFile(f, 'rb') as compressed:
            while True:
                # Read header: timestamp(Q) length(H) delay(f)
                header = compressed.read(14)
                if not header:
                    break
                    
                ts, length, delay = struct.unpack('!QHf', header)
                # Skip packet data
                compressed.read(length)
                delays.append(delay)
    
    return {
        'delays': delays,
        'min_delay': min(delays),
        'max_delay': max(delays),
        'mean_delay': np.mean(delays),
        'median_delay': np.median(delays),
        'std_delay': np.std(delays),
        'p95_delay': np.percentile(delays, 95),
        'p99_delay': np.percentile(delays, 99),
    }

def analyze_loss_log(log_file: Path):
    """Analyze packet loss emulator log file"""
    dropped_packets = 0
    total_packets = 0
    
    with open(log_file, 'rb') as f:
        with lz4.frame.LZ4FrameFile(f, 'rb') as compressed:
            while True:
                # Read header: timestamp(Q) length(H) dropped(?)
                header = compressed.read(11)
                if not header:
                    break
                    
                ts, length, dropped = struct.unpack('!QH?', header)
                # Skip packet data
                compressed.read(length)
                
                total_packets += 1
                if dropped:
                    dropped_packets += 1
    
    return {
        'total_packets': total_packets,
        'dropped_packets': dropped_packets,
        'loss_rate': dropped_packets / total_packets if total_packets > 0 else 0
    }

def analyze_reorder_log(log_file: Path):
    """Analyze packet reorder emulator log file"""
    reorder_numbers = []
    
    with open(log_file, 'rb') as f:
        with lz4.frame.LZ4FrameFile(f, 'rb') as compressed:
            while True:
                # Read header: timestamp(Q) length(H) orig_pos(i) new_pos(i)
                header = compressed.read(18)
                if not header:
                    break
                    
                ts, length, orig_pos, new_pos = struct.unpack('!QHii', header)
                # Skip packet data
                compressed.read(length)
                
                reorder_number = abs(orig_pos - new_pos)
                reorder_numbers.append(reorder_number)
    
    ordered_packets = sum(1 for r in reorder_numbers if r == 0)
    
    return {
        'reorder_numbers': reorder_numbers,
        'max_reorder': max(reorder_numbers),
        'mean_reorder': np.mean(reorder_numbers),
        'median_reorder': np.median(reorder_numbers),
        'std_reorder': np.std(reorder_numbers),
        'ordered_packets': ordered_packets,
        'ordered_ratio': ordered_packets / len(reorder_numbers)
    }

def run_scenario(scenario_num, config_path='./src/netfi/canonical_configs/'):
    """Run specified test scenario"""
    config = {}
    config_files = Path(config_path).glob('*.json')
    for config_file in config_files:
        with open(config_file) as f:
            # Load individual config
            emulator_config = json.load(f)
            # Get emulator name from filename
            emulator_name = config_file.stem
            # Add to master config
            config[emulator_name] = emulator_config
    print(config)
    return
    
    
    NUM_PACKETS = 10_000
    START_PORT = 5000
    LOG_DIR = f"logs/scenario_{scenario_num}"
    
    scenarios = {
        1: [DelayEmulator],  # Test each emulator individually
        2: [DelayEmulator, PacketLossEmulator],
        3: [PacketLossEmulator, PacketReorderEmulator],
        4: [DelayEmulator, PacketReorderEmulator],
        5: [PacketLossEmulator, DelayEmulator, PacketReorderEmulator]
    }
    
    if scenario_num not in scenarios:
        raise ValueError(f"Invalid scenario number: {scenario_num}")
    
    # Create network emulator with logging
    emulator = NetworkEmulator(
        pipeline=scenarios[scenario_num],
        master_config=config,
        input_port=START_PORT,
        output_port=START_PORT + len(scenarios[scenario_num]),
        output_ip='127.0.0.1',
        log_path=LOG_DIR
    )
    
    # Rest of test execution remains the same
    receiver_thread = ThreadWithReturn(
        target=packet_receiver,
        args=(emulator.output_port, NUM_PACKETS)
    )
    receiver_thread.start()
    
    emulator.start()
    time.sleep(1)
    
    sender_thread = threading.Thread(
        target=packet_sender,
        args=('localhost', emulator.input_port, NUM_PACKETS)
    )
    sender_thread.start()
    
    sender_thread.join()
    packet_data = receiver_thread.join()
    emulator.stop()
    
    # Analyze logs and visualize
    stats = analyze_emulator_logs(LOG_DIR, scenarios[scenario_num])
    stats.update(packet_data)  # Add receiver stats
    visualize_scenario(stats, f"Scenario {scenario_num}")
    
    return stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Network Emulator Scenario Tests')
    parser.add_argument('scenario', type=int, choices=range(1, 6),
                      help='Scenario number (1-5)')
    parser.add_argument('--config_dir', default='./src/netfi/canonical_configs/',
                        help='Path to the directory containing the emulator config files')
    
    
    args = parser.parse_args()
    
    try:
        stats = run_scenario(args.scenario, args.config_dir)
    except Exception as e:
        print(f"Error running scenario {args.scenario}: {str(e)}")
        raise

