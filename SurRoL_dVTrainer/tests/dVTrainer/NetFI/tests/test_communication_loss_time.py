import sys
import os
import time
import threading
import socket
import struct
import random
import string
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import lz4.frame
from tqdm import tqdm

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from netfi.models.communication_loss_model import CommunicationLossModel
from netfi.emulators.packet_loss_emulator import PacketLossEmulator

def generate_random_payload(length=32):
    """Generate random string payload"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length)).encode()

def packet_sender(host: str, port: int, duration_ms: int, packet_interval_ms: int):
    """
    Send UDP packets with sequence numbers for a specified duration.
    
    Args:
        host: Target host
        port: Target port
        duration_ms: Total duration to send packets in milliseconds
        packet_interval_ms: Interval between packets in milliseconds
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[Sender] Starting to send packets for {duration_ms}ms with {packet_interval_ms}ms interval...")
    start_time = time.time() * 1000  # Convert to milliseconds
    seq_num = 0
    
    while (time.time() * 1000 - start_time) < duration_ms:
        # Create packet with sequence number and random payload
        data = struct.pack('!I', seq_num) + generate_random_payload(32)
        sock.sendto(data, (host, port))
        seq_num += 1
        
        # Progress reporting
        if seq_num % 100 == 0:
            elapsed = time.time() * 1000 - start_time
            print(f"[Sender] Sent {seq_num} packets ({elapsed/duration_ms:.0%} complete)")
        
        # Sleep for the specified interval
        time.sleep(packet_interval_ms / 1000)  # Convert to seconds
    
    sock.close()
    print(f"[Sender] Completed sending {seq_num} packets")

def packet_receiver(port: int, duration_ms: int):
    """
    Receive UDP packets and track statistics for a specified duration.
    
    Args:
        port: Port to listen on
        duration_ms: Total duration to receive packets in milliseconds
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', port))
    sock.settimeout(1.0)  # 1 second timeout
    
    print(f"[Receiver] Starting to receive packets on port {port} for {duration_ms}ms...")
    received_packets = set()
    start_time = time.time() * 1000  # Convert to milliseconds
    
    while (time.time() * 1000 - start_time) < duration_ms:
        try:
            data, addr = sock.recvfrom(4096)
            seq_num = struct.unpack('!I', data[:4])[0]
            received_packets.add(seq_num)
            
            # Progress reporting
            if len(received_packets) % 100 == 0:
                elapsed = time.time() * 1000 - start_time
                print(f"[Receiver] Received {len(received_packets)} packets ({elapsed/duration_ms:.0%} complete)")
        except socket.timeout:
            continue
    
    sock.close()
    print(f"[Receiver] Completed receiving {len(received_packets)} packets")
    return received_packets

def analyze_time_based_loss(log_file: str):
    """Analyze packet log and compute time-based statistics"""
    print(f"[Analyzer] Starting analysis of {log_file}...")
    lost_packets = []
    current_burst = 0
    burst_lengths = []
    total_packets = 0
    timestamps = []
    
    # Track loss periods
    loss_periods = []  # List of (start_time, end_time, packets_lost) tuples
    current_loss_start = None
    current_loss_packets = 0
    
    with lz4.frame.open(log_file, 'rb') as f:
        while True:
            header = f.read(11)  # Q(8) + H(2) + ?(1)
            if not header or len(header) < 11:
                break
            ts, length, dropped = struct.unpack("!QH?", header)
            data = f.read(length)
            if len(data) < length:
                break
                
            seq = struct.unpack('!I', data[:4])[0]
            total_packets = max(total_packets, seq + 1)
            timestamps.append(ts)
            
            if dropped:
                lost_packets.append(seq)
                current_burst += 1
                current_loss_packets += 1
                if current_loss_start is None:
                    current_loss_start = ts
            else:
                if current_burst > 0:
                    burst_lengths.append(current_burst)
                    current_burst = 0
                if current_loss_start is not None:
                    loss_periods.append((current_loss_start, ts, current_loss_packets))
                    current_loss_start = None
                    current_loss_packets = 0
    
    # Final burst if log ends with loss
    if current_burst > 0:
        burst_lengths.append(current_burst)
    if current_loss_start is not None:
        loss_periods.append((current_loss_start, timestamps[-1], current_loss_packets))
    
    # Calculate time-based statistics
    if timestamps:
        total_duration = (timestamps[-1] - timestamps[0]) / 1e6  # Convert to milliseconds
        avg_packet_interval = total_duration / len(timestamps)
    else:
        total_duration = 0
        avg_packet_interval = 0
    
    # Calculate loss period statistics
    loss_durations = [(end - start) / 1e6 for start, end, _ in loss_periods]  # Convert to milliseconds
    avg_loss_duration = np.mean(loss_durations) if loss_durations else 0
    max_loss_duration = max(loss_durations) if loss_durations else 0
    
    return {
        'total_packets': total_packets,
        'lost_packets': lost_packets,
        'loss_rate': len(lost_packets) / max(1, total_packets),
        'burst_lengths': burst_lengths,
        'total_bursts': len(burst_lengths),
        'mean_bll': np.mean(burst_lengths) if burst_lengths else 0,
        'std_bll': np.std(burst_lengths) if burst_lengths else 0,
        'max_bll': max(burst_lengths) if burst_lengths else 0,
        'total_duration_ms': total_duration,
        'avg_packet_interval_ms': avg_packet_interval,
        'loss_periods': loss_periods,
        'loss_durations': loss_durations,
        'avg_loss_duration_ms': avg_loss_duration,
        'max_loss_duration_ms': max_loss_duration
    }

def visualize_time_based_results(stats, params):
    """Visualize time-based packet loss statistics"""
    plt.style.use('ggplot')
    fig = plt.figure(figsize=(15, 15))
    
    # Create a 3x2 grid of subplots
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
    
    # Burst Length Distribution - Position (0,0)
    ax1 = fig.add_subplot(gs[0, 0])
    burst_lengths = stats['burst_lengths']
    if burst_lengths:
        max_burst = max(burst_lengths)
        bins = np.arange(1, max_burst + 2) - 0.5
        ax1.hist(burst_lengths, bins=bins, color='#3498db', edgecolor='black', linewidth=0.5)
        ax1.set_title('Burst Length Distribution', fontsize=14)
        ax1.set_xlabel('Burst Length (packets)')
        ax1.set_ylabel('Frequency')
    else:
        ax1.text(0.5, 0.5, "No burst data available", 
                ha='center', va='center', fontsize=12)
    
    # Loss Duration Distribution - Position (0,1)
    ax2 = fig.add_subplot(gs[0, 1])
    loss_durations = stats['loss_durations']
    if loss_durations:
        max_duration = max(loss_durations)
        bins = np.linspace(0, max_duration, 20)
        ax2.hist(loss_durations, bins=bins, color='#e74c3c', edgecolor='black', linewidth=0.5)
        ax2.set_title('Loss Duration Distribution', fontsize=14)
        ax2.set_xlabel('Duration (ms)')
        ax2.set_ylabel('Frequency')
    else:
        ax2.text(0.5, 0.5, "No loss duration data available", 
                ha='center', va='center', fontsize=12)
    
    # Packet Loss Pattern - Position (1,0)
    ax3 = fig.add_subplot(gs[1, 0])
    grid_size = min(100, int(np.sqrt(stats['total_packets'])))
    packet_grid = np.zeros((grid_size, grid_size))
    lost_set = set(stats['lost_packets'])
    
    for seq in range(min(stats['total_packets'], grid_size*grid_size)):
        i, j = divmod(seq, grid_size)
        if seq in lost_set:
            packet_grid[i][j] = 1
            
    cmap = plt.cm.colors.ListedColormap(['#2ecc71', '#e74c3c'])
    ax3.imshow(packet_grid, cmap=cmap, interpolation='none', aspect='equal')
    ax3.set_title('Packet Loss Pattern', fontsize=14)
    ax3.axis('off')
    
    # Loss Periods Timeline - Position (1,1)
    ax4 = fig.add_subplot(gs[1, 1])
    loss_periods = stats['loss_periods']
    if loss_periods:
        # Convert timestamps to relative time in milliseconds
        start_time = loss_periods[0][0]
        times = [(start - start_time) / 1e6 for start, _, _ in loss_periods]
        durations = [(end - start) / 1e6 for start, end, _ in loss_periods]
        packets = [packets for _, _, packets in loss_periods]
        
        # Create scatter plot with size proportional to packets lost
        scatter = ax4.scatter(times, durations, s=np.array(packets)*2, alpha=0.6, c='#e74c3c')
        ax4.set_title('Loss Periods Timeline', fontsize=14)
        ax4.set_xlabel('Time (ms)')
        ax4.set_ylabel('Duration (ms)')
        
        # Add legend for packet counts
        sizes = [10, 50, 100]
        labels = [f'{size} packets' for size in sizes]
        handles = [plt.scatter([], [], s=size*2, c='#e74c3c', alpha=0.6) for size in sizes]
        ax4.legend(handles, labels, title='Packets Lost')
    else:
        ax4.text(0.5, 0.5, "No loss periods data available", 
                ha='center', va='center', fontsize=12)
    
    # Statistics Panel - Position (2,0)
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.axis('off')
    
    stats_text = [
        "Time-Based Communication Loss Statistics",
        f"Total Duration: {stats['total_duration_ms']:.1f}ms",
        f"Average Packet Interval: {stats['avg_packet_interval_ms']:.1f}ms",
        f"Total Packets: {stats['total_packets']}",
        f"Lost Packets: {len(stats['lost_packets'])}",
        f"Loss Rate: {stats['loss_rate']:.2%}",
        f"Total Bursts: {stats['total_bursts']}",
        f"Mean Burst Length: {stats['mean_bll']:.2f}",
        f"Std Dev Burst Length: {stats['std_bll']:.2f}",
        f"Max Burst Length: {stats['max_bll']}",
        f"Average Loss Duration: {stats['avg_loss_duration_ms']:.1f}ms",
        f"Max Loss Duration: {stats['max_loss_duration_ms']:.1f}ms"
    ]
    
    ax5.text(0.05, 0.95, "\n".join(stats_text), 
            fontsize=12, va='top', linespacing=1.5,
            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=1'))
    
    # Model Parameters - Position (2,1)
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.axis('off')
    
    params_text = [
        "Model Parameters",
        f"Loss Probability: {params.get('loss_prob', 0.01):.4f}",
        f"Min Loss Length: {params.get('min_loss_length', 1)}ms",
        f"Max Loss Length: {params.get('max_loss_length', 5)}ms",
        f"Cooldown Period: {params.get('cooldown_period', 10)}ms",
        f"Unit: {params.get('unit', 'milliseconds')}"
    ]
    
    ax6.text(0.05, 0.95, "\n".join(params_text), 
            fontsize=12, va='top', linespacing=1.5,
            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=1'))
    
    plt.tight_layout()
    plt.savefig("communication_loss_time_results.png", dpi=150)
    plt.show()

if __name__ == "__main__":
    # Configuration
    EMULATOR_PORT = 5000
    RECEIVER_PORT = 5001
    TEST_DURATION_MS = 30000  # 30 seconds
    PACKET_INTERVAL_MS = 10   # 10ms between packets
    LOG_FILE = "communication_loss_time_log.bin"
    NUM_SIMULATIONS = 15
    
    # Define model parameters for time-based unit
    comm_loss_params = {
        'loss_prob': 1,           # 100% chance of entering loss period
        'min_loss_length': 0,     # Minimum 0ms lost in a burst
        'max_loss_length': 3000,  # Maximum 3000ms lost in a burst
        'cooldown_period': 3000,  # 3000ms cooldown after a burst
        'unit': 'milliseconds'
    }
    
    # Create full params structure for the emulator
    params = {
        'Communication_Loss': comm_loss_params
    }
    
    # Track statistics across simulations
    all_loss_rates = []
    all_mean_bursts = []
    all_total_bursts = []
    all_avg_durations = []
    all_max_durations = []
    
    print(f"\n[Main] Running {NUM_SIMULATIONS} simulations...")
    
    for sim_num in range(NUM_SIMULATIONS):
        print(f"\n[Main] Starting simulation {sim_num + 1}/{NUM_SIMULATIONS}")
        
        # Start Network Emulator
        print("[Main] Starting network emulator...")
        pl_emulator = PacketLossEmulator(
            input_port=EMULATOR_PORT,
            output_port=RECEIVER_PORT,
            model_name='Communication_Loss',
            params=params,
            protocol='udp',
            log_packets=True,
            log_path=LOG_FILE
        )
        
        # Start receiver first
        print("[Main] Starting receiver thread...")
        receiver_thread = threading.Thread(
            target=packet_receiver, 
            args=(RECEIVER_PORT, TEST_DURATION_MS)
        )
        receiver_thread.start()
        
        # Start emulator
        print("[Main] Starting emulator...")
        pl_emulator.start()
        time.sleep(1)  # Wait for emulator to initialize
        
        # Start sender
        print("[Main] Starting sender thread...")
        sender_thread = threading.Thread(
            target=packet_sender,
            args=('localhost', EMULATOR_PORT, TEST_DURATION_MS, PACKET_INTERVAL_MS)
        )
        sender_thread.start()
        
        # Wait for completion
        print("[Main] Test running...")
        sender_thread.join()
        print("[Main] Sender thread completed")
        receiver_thread.join()
        print("[Main] Receiver thread completed")
        
        print("[Main] Stopping emulator...")
        pl_emulator.stop()
        print("[Main] Emulator stopped")
        
        # Analyze results
        print("\n[Main] Analyzing emulation results...")
        stats = analyze_time_based_loss(LOG_FILE)
        
        # Store statistics
        all_loss_rates.append(stats['loss_rate'])
        all_mean_bursts.append(stats['mean_bll'])
        all_total_bursts.append(stats['total_bursts'])
        all_avg_durations.append(stats['avg_loss_duration_ms'])
        all_max_durations.append(stats['max_loss_duration_ms'])
        
        print(f"[Simulation {sim_num + 1}] Loss rate: {stats['loss_rate']:.2%}, "
              f"Mean burst length: {stats['mean_bll']:.2f}, "
              f"Total bursts: {stats['total_bursts']}, "
              f"Avg duration: {stats['avg_loss_duration_ms']:.1f}ms, "
              f"Max duration: {stats['max_loss_duration_ms']:.1f}ms")
    
    # Calculate and print average statistics
    print("\n[Main] Average statistics across all simulations:")
    print(f"Average Loss Rate: {np.mean(all_loss_rates):.2%} ± {np.std(all_loss_rates):.2%}")
    print(f"Average Mean Burst Length: {np.mean(all_mean_bursts):.2f} ± {np.std(all_mean_bursts):.2f}")
    print(f"Average Total Bursts: {np.mean(all_total_bursts):.1f} ± {np.std(all_total_bursts):.1f}")
    print(f"Average Loss Duration: {np.mean(all_avg_durations):.1f}ms ± {np.std(all_avg_durations):.1f}ms")
    print(f"Average Max Duration: {np.mean(all_max_durations):.1f}ms ± {np.std(all_max_durations):.1f}ms")
    
    # Plot only the last simulation
    print("\n[Main] Visualizing results from last simulation:")
    visualize_time_based_results(stats, comm_loss_params) 