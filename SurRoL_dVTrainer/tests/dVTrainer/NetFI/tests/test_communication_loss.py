import sys
import os
import json
import time
import socket
import threading
import struct
import random
import string
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
from scipy import stats
import lz4.frame
from tqdm import tqdm

from test_utils import ThreadWithReturn

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from netfi.models.communication_loss_model import CommunicationLossModel
from netfi.emulators.communication_loss_emulator import CommunicationLossEmulator

# Helper class for threads that return values

def generate_random_payload(length=32):
    """Generate random string payload"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length)).encode()

def packet_sender(host: str, port: int, num_packets: int):
    """Send UDP packets with sequence numbers"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[Sender] Starting to send {num_packets} packets...")
    start_time = time.time()
    
    for i in range(num_packets):
        # Create packet with sequence number and random payload
        data = struct.pack('!I', i) + generate_random_payload(32)
        sock.sendto(data, (host, port))
        
        # Progress reporting
        if i % 2000 == 0 and i > 0:
            print(f"[Sender] Sent {i}/{num_packets} packets ({i/num_packets:.0%})")
    
    sock.close()
    duration = time.time() - start_time
    print(f"[Sender] Completed in {duration:.2f}s ({num_packets/duration:.0f} pkt/s)")

def packet_receiver(port: int, num_packets: int):
    """Receive UDP packets and track statistics"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', port))
    sock.settimeout(5.0)  # 5 second timeout
    
    print(f"[Receiver] Starting to receive packets on port {port}...")
    received_packets = set()
    start_time = time.time()
    
    try:
        while len(received_packets) < num_packets:
            try:
                data, addr = sock.recvfrom(4096)
                seq_num = struct.unpack('!I', data[:4])[0]
                received_packets.add(seq_num)
                
                # Progress reporting
                if len(received_packets) % 2000 == 0:
                    print(f"[Receiver] Received {len(received_packets)}/{num_packets} packets "
                          f"({len(received_packets)/num_packets:.0%})")
            except socket.timeout:
                print("[Receiver] Timeout waiting for packets")
                break
    except Exception as e:
        print(f"[Receiver] Error: {e}")
    finally:
        sock.close()
    
    duration = time.time() - start_time
    print(f"[Receiver] Completed in {duration:.2f}s, received {len(received_packets)}/{num_packets} packets")
    return received_packets

def analyze_log(log_file: str):
    """Analyze packet log and compute statistics"""
    print(f"[Analyzer] Starting analysis of {log_file}...")
    start_time = time.time()
    lost_packets = []
    current_burst = 0
    burst_lengths = []
    total_packets = 0
    
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
            
            if dropped:
                lost_packets.append(seq)
                current_burst += 1
            elif current_burst > 0:
                burst_lengths.append(current_burst)
                current_burst = 0
    
    # Final burst if log ends with loss
    if current_burst > 0:
        burst_lengths.append(current_burst)
        
    duration = time.time() - start_time
    print(f"[Analyzer] Completed in {duration:.2f}s ({total_packets/duration:.0f} pkt/s)")
    
    return {
        'total_packets': total_packets,
        'lost_packets': lost_packets,
        'loss_rate': len(lost_packets) / max(1, total_packets),
        'burst_lengths': burst_lengths,
        'total_bursts': len(burst_lengths),
        'mean_bll': np.mean(burst_lengths) if burst_lengths else 0,
        'std_bll': np.std(burst_lengths) if burst_lengths else 0,
        'max_bll': max(burst_lengths) if burst_lengths else 0
    }

def simulate_communication_loss(params, total_packets=100000):
    """Simulate the Communication Loss Model directly"""
    model = CommunicationLossModel(params)
    
    # Track statistics
    lost_packets = []
    current_burst = 0
    burst_lengths = []
    
    for seq_num in range(total_packets):
        dropped = model.should_drop()
        
        if dropped:
            lost_packets.append(seq_num)
            current_burst += 1
        elif current_burst > 0:
            burst_lengths.append(current_burst)
            current_burst = 0
    
    # Final burst if simulation ends with loss
    if current_burst > 0:
        burst_lengths.append(current_burst)
    
    loss_rate = len(lost_packets) / total_packets
    
    return {
        'total_packets': total_packets,
        'lost_packets': lost_packets,
        'loss_rate': loss_rate,
        'burst_lengths': burst_lengths,
        'total_bursts': len(burst_lengths),
        'mean_bll': np.mean(burst_lengths) if burst_lengths else 0,
        'std_bll': np.std(burst_lengths) if burst_lengths else 0,
        'max_bll': max(burst_lengths) if burst_lengths else 0
    }

def calculate_theoretical_loss_rate(params):
    """Calculate theoretical packet loss rate for Communication Loss Model"""
    loss_prob = params.get('loss_prob', 0.01)
    min_loss = params.get('min_loss_length', 1)
    max_loss = params.get('max_loss_length', 5)
    cooldown = params.get('cooldown_period', 10)
    
    # Average burst length
    avg_burst_length = (min_loss + max_loss) / 2
    
    # Average cycle length (burst + cooldown)
    avg_cycle_length = avg_burst_length + cooldown
    
    # Probability of being in a burst state
    p_burst = loss_prob * avg_burst_length / avg_cycle_length
    
    return p_burst

def visualize_results(stats, params):
    """Visualize packet loss statistics"""
    plt.style.use('ggplot')
    fig = plt.figure(figsize=(15, 10))
    
    # Create a 2x2 grid of subplots
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
    
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
    
    # Packet Loss Pattern - Position (0,1)
    ax2 = fig.add_subplot(gs[0, 1])
    grid_size = min(100, int(np.sqrt(stats['total_packets'])))
    packet_grid = np.zeros((grid_size, grid_size))
    lost_set = set(stats['lost_packets'])
    
    for seq in range(min(stats['total_packets'], grid_size*grid_size)):
        i, j = divmod(seq, grid_size)
        if seq in lost_set:
            packet_grid[i][j] = 1
            
    cmap = plt.cm.colors.ListedColormap(['#2ecc71', '#e74c3c'])
    ax2.imshow(packet_grid, cmap=cmap, interpolation='none', aspect='equal')
    ax2.set_title('Packet Loss Pattern', fontsize=14)
    ax2.axis('off')
    
    # Statistics Panel - Position (1,0)
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.axis('off')
    
    # Calculate theoretical loss rate
    theoretical_loss = calculate_theoretical_loss_rate(params)
    print(f"Theoretical loss rate: {theoretical_loss}")
    
    stats_text = [
        "Communication Loss Model Statistics",
        f"Total Packets: {stats['total_packets']}",
        f"Lost Packets: {len(stats['lost_packets'])}",
        f"Loss Rate: {stats['loss_rate']:.2%} (Theoretical: {theoretical_loss:.2%})",
        f"Total Bursts: {stats['total_bursts']}",
        f"Mean Burst Length: {stats['mean_bll']:.2f}",
        f"Std Dev Burst Length: {stats['std_bll']:.2f}",
        f"Max Burst Length: {stats['max_bll']}"
    ]
    
    ax3.text(0.05, 0.95, "\n".join(stats_text), 
            fontsize=12, va='top', linespacing=1.5,
            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=1'))
    
    # Model Parameters - Position (1,1)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis('off')
    
    params_text = [
        "Model Parameters",
        f"Loss Probability: {params.get('loss_prob', 0.01):.4f}",
        f"Min Loss Length: {params.get('min_loss_length', 1)}",
        f"Max Loss Length: {params.get('max_loss_length', 5)}",
        f"Cooldown Period: {params.get('cooldown_period', 10)}"
    ]
    
    ax4.text(0.05, 0.95, "\n".join(params_text), 
            fontsize=12, va='top', linespacing=1.5,
            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=1'))
    
    plt.tight_layout()
    plt.savefig("communication_loss_results.png", dpi=150)
    plt.show()

def compare_simulation_vs_emulation(sim_stats, emu_stats):
    """Compare simulation vs emulation results"""
    plt.style.use('ggplot')
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # Burst Length Distribution Comparison
    ax1 = axes[0]
    sim_bursts = sim_stats['burst_lengths']
    emu_bursts = emu_stats['burst_lengths']
    
    max_burst = max(max(sim_bursts, default=0), max(emu_bursts, default=0))
    bins = np.arange(1, max_burst + 2) - 0.5
    
    if sim_bursts:
        ax1.hist(sim_bursts, bins=bins, alpha=0.7, label='Simulation', 
                color='#3498db', edgecolor='black', linewidth=0.5)
    if emu_bursts:
        ax1.hist(emu_bursts, bins=bins, alpha=0.7, label='Emulation', 
                color='#e74c3c', edgecolor='black', linewidth=0.5)
    
    ax1.set_title('Burst Length Distribution Comparison', fontsize=14)
    ax1.set_xlabel('Burst Length (packets)')
    ax1.set_ylabel('Frequency')
    ax1.legend()
    
    # Statistics Comparison
    ax2 = axes[1]
    ax2.axis('off')
    
    comparison_text = [
        "Simulation vs Emulation Comparison",
        f"Simulation Loss Rate: {sim_stats['loss_rate']:.2%}",
        f"Emulation Loss Rate: {emu_stats['loss_rate']:.2%}",
        f"Simulation Mean BLL: {sim_stats['mean_bll']:.2f}",
        f"Emulation Mean BLL: {emu_stats['mean_bll']:.2f}",
        f"Simulation Total Bursts: {sim_stats['total_bursts']}",
        f"Emulation Total Bursts: {emu_stats['total_bursts']}",
        f"Simulation Max BLL: {sim_stats['max_bll']}",
        f"Emulation Max BLL: {emu_stats['max_bll']}"
    ]
    
    ax2.text(0.05, 0.95, "\n".join(comparison_text), 
            fontsize=12, va='top', linespacing=1.5,
            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=1'))
    
    plt.tight_layout()
    plt.savefig("communication_loss_comparison.png", dpi=150)
    plt.show()

if __name__ == "__main__":
    # Configuration
    EMULATOR_PORT = 5000
    RECEIVER_PORT = 5001
    NUM_PACKETS = 10000
    LOG_FILE = "communication_loss_log.bin"
    
    # Define model parameters for packet-based unit
    packet_based_params = {
        'loss_prob': 0.02,        # 2% chance of entering loss period
        'min_loss_length': 100,   # Minimum 100 packets lost in a burst
        'max_loss_length': 500,   # Maximum 500 packets lost in a burst
        'cooldown_period': 500,   # 500 packet cooldown after a burst
        'unit': 'packet'
    }
    
    # Define model parameters for time-based unit
    time_based_params = {
        'loss_prob': 0.02,        # 2% chance of entering loss period
        'min_loss_length': 100,   # Minimum 100ms lost in a burst
        'max_loss_length': 500,   # Maximum 500ms lost in a burst
        'cooldown_period': 500,   # 500ms cooldown after a burst
        'unit': 'milliseconds'
    }
    
    # Choose which parameters to use
    comm_loss_params = time_based_params  # Change to packet_based_params to test packet-based unit
    
    # Create full params structure for the emulator
    params = {
        'Communication_Loss': comm_loss_params
    }
    
    # Run direct simulation first
    print("\n[Main] Running direct simulation...")
    sim_stats = simulate_communication_loss(comm_loss_params, NUM_PACKETS)
    print(f"[Simulation] Loss rate: {sim_stats['loss_rate']:.2%}, "
          f"Mean burst length: {sim_stats['mean_bll']:.2f}, "
          f"Total bursts: {sim_stats['total_bursts']}")
    
    # Start Network Emulator
    print("\n[Main] Starting network emulator...")
    pl_emulator = CommunicationLossEmulator(
        input_port=EMULATOR_PORT,
        output_port=RECEIVER_PORT,
        params=params,
        protocol='udp',
        log_packets=True,
        log_path=LOG_FILE
    )
    
    # Start receiver first
    print("[Main] Starting receiver thread...")
    receiver_thread = threading.Thread(
        target=packet_receiver, 
        args=(RECEIVER_PORT, NUM_PACKETS)
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
        args=('localhost', EMULATOR_PORT, NUM_PACKETS)
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
    
    # Analyze and visualize
    print("\n[Main] Analyzing emulation results...")
    emu_stats = analyze_log(LOG_FILE)
    print(f"[Emulation] Loss rate: {emu_stats['loss_rate']:.2%}, "
          f"Mean burst length: {emu_stats['mean_bll']:.2f}, "
          f"Total bursts: {emu_stats['total_bursts']}")
    
    print("\n[Main] Visualizing simulation results:")
    visualize_results(sim_stats, comm_loss_params)
    
    print("\n[Main] Comparing simulation vs emulation:")
    compare_simulation_vs_emulation(sim_stats, emu_stats)
