import numpy as np
import matplotlib.pyplot as plt
from netfi.emulators.delay_emulator import DelayEmulator
import threading
import time
import socket
import struct
import lz4
import random
import string
import seaborn as sns
from collections import defaultdict
import json

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
        # Pack sequence number (I), timestamp (Q), and payload
        data = struct.pack(f'!IQ{len(payload)}s', i, timestamp, payload)
        sock.sendto(data, (host, port))
        
        if i % 5000 == 0 and i > 0:
            print(f"[Sender] Sent {i}/{num_packets} packets ({i/num_packets:.0%})")
    
    sock.close()
    duration = time.time() - start_time
    print(f"[Sender] Completed in {duration:.2f}s ({num_packets/duration:.0f} pkt/s)")

def packet_receiver(port: int, num_packets: int):
    """Receive UDP packets and track delays"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', port))
    sock.settimeout(5)  # Set receive timeout to 5 seconds
    
    delays = {}  # {sequence_number: (send_time, receive_time)}
    print(f"[Receiver] Listening on port {port} for {num_packets} packets...")
    start_time = time.time()
    last_print = 0
    last_received = 0
    timeout_counter = 0
    
    while len(delays) < num_packets and timeout_counter < 3:
        try:
            data, _ = sock.recvfrom(4096)
            receive_time = time.time_ns()
            
            # Unpack header (sequence number and timestamp)
            seq, send_time = struct.unpack('!IQ', data[:12])
            delays[seq] = (send_time, receive_time)
            
            last_received = time.time()
            timeout_counter = 0
            
            if time.time() - last_print > 2:
                print(f"[Receiver] Received {len(delays)}/{num_packets} packets ({len(delays)/num_packets:.0%})")
                last_print = time.time()
        
        except socket.timeout:
            if time.time() - last_received > 10:
                timeout_counter += 1
                print(f"[Receiver] Timeout {timeout_counter}/3 - No packets received for 10 seconds")
            continue
    
    sock.close()
    duration = time.time() - start_time
    print(f"[Receiver] Completed in {duration:.2f}s ({len(delays)/duration:.0f} pkt/s)")
    return delays

def analyze_delays(delays):
    """Analyze delay measurements and compute statistics"""
    print("[Analyzer] Computing delay statistics...")
    delay_values = []
    
    for seq in sorted(delays.keys()):
        send_time, recv_time = delays[seq]
        delay_ms = (recv_time - send_time) / 1_000_000  # Convert ns to ms
        delay_values.append(delay_ms)
    
    stats = {
        'total_packets': len(delays),
        'min_delay': np.min(delay_values),
        'max_delay': np.max(delay_values),
        'mean_delay': np.mean(delay_values),
        'median_delay': np.median(delay_values),
        'std_delay': np.std(delay_values),
        'p95_delay': np.percentile(delay_values, 95),
        'p99_delay': np.percentile(delay_values, 99),
        'delays': delay_values
    }
    return stats

def visualize_results(stats):
    """Create visualization of delay statistics"""
    print("[Visualization] Generating plots...")
    plt.style.use('ggplot')
    fig = plt.figure(figsize=(20, 10))
    
    # Create grid layout
    gs = fig.add_gridspec(2, 3, width_ratios=[1, 1.5, 0.5])
    
    # Delay Distribution Histogram
    ax1 = fig.add_subplot(gs[0, 0])
    sns.histplot(data=stats['delays'], bins=50, ax=ax1, 
                color='#2e86de', edgecolor='#1a3c6d')
    ax1.set_title('Delay Distribution', fontsize=14, pad=20)
    ax1.set_xlabel('Delay (ms)', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    
    # Delay Heatmap
    ax2 = fig.add_subplot(gs[:, 1])
    grid_width = 1000
    grid_height = 1000
    delay_grid = np.zeros((grid_height, grid_width))
    delays_normalized = np.array(stats['delays'])
    delays_normalized = (delays_normalized - stats['min_delay']) / (stats['max_delay'] - stats['min_delay'])
    
    print("[Visualization] Creating delay grid...")
    for i, delay in enumerate(delays_normalized):
        row = i % grid_height
        col = i // grid_height
        if col < grid_width:
            delay_grid[row][col] = delay
    
    print("[Visualization] Generating heatmap...")
    # Create heatmap with separate colorbar
    heatmap = sns.heatmap(delay_grid, cmap='viridis', ax=ax2,
                         xticklabels=False, yticklabels=False)
    colorbar = heatmap.collections[0].colorbar
    colorbar.set_label('Normalized Delay', fontsize=10)
    ax2.set_title('Packet Delay Pattern', fontsize=14, pad=20)
    
    # Statistics Panel
    ax3 = fig.add_subplot(gs[:, 2])
    ax3.axis('off')
    
    stats_text = [
        "Network Delay Statistics",
        "─" * 25,
        f"Total Packets: {stats['total_packets']:,}",
        f"Min Delay: {stats['min_delay']:.2f} ms",
        f"Max Delay: {stats['max_delay']:.2f} ms",
        f"Mean Delay: {stats['mean_delay']:.2f} ms",
        f"Median Delay: {stats['median_delay']:.2f} ms",
        f"Std Dev: {stats['std_delay']:.2f} ms",
        f"95th Percentile: {stats['p95_delay']:.2f} ms",
        f"99th Percentile: {stats['p99_delay']:.2f} ms"
    ]
    
    ax3.text(0.1, 0.7, "\n".join(stats_text),
            fontsize=12, linespacing=1.8,
            color='#2d3436', fontfamily='monospace',
            bbox=dict(facecolor='#f8f9fa', edgecolor='#dfe6e9',
                    boxstyle='round,pad=1'))
    
    # Add CDF plot
    ax4 = fig.add_subplot(gs[1, 0])
    sorted_delays = np.sort(stats['delays'])
    cumulative = np.arange(1, len(sorted_delays) + 1) / len(sorted_delays)
    ax4.plot(sorted_delays, cumulative, color='#2e86de', linewidth=2)
    ax4.set_title('Cumulative Distribution Function', fontsize=14, pad=20)
    ax4.set_xlabel('Delay (ms)', fontsize=12)
    ax4.set_ylabel('Cumulative Probability', fontsize=12)
    ax4.grid(True)
    
    plt.suptitle("Network Delay Analysis",
                fontsize=18, y=0.98,
                color='#2d3436', fontweight='bold')
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()
    print("[Visualization] Displaying results window")

def plot_state_timeline(states: list, lost_packets: list, num_packets: int):
    """
    Plot the state timeline with color bars and burst loss length histogram.
    
    Args:
        states: List of states at each packet
        lost_packets: List of lost packet indices
        num_packets: Total number of packets
    """
    # Create figure with three subplots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12), height_ratios=[1, 2, 1])
    
    # Color mapping for states with milder colors
    state_colors = {
        'Good': '#4A90E2',      # Soft blue
        'Bad': '#F5A623',       # Soft yellow
        'Intermediate1': '#9B6B9E',  # Soft purple
        'Intermediate2': '#A9A9A9'   # Soft gray
    }
    
    # Convert hex colors to RGB values
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4))
    
    # Create state timeline with RGB values
    state_sequence = np.array([hex_to_rgb(state_colors[state]) for state in states])
    
    # Plot state timeline
    ax1.imshow(state_sequence.reshape(1, -1, 3), aspect='auto', interpolation='nearest')
    ax1.set_yticks([])
    ax1.set_title('Model State Timeline', fontsize=14)
    
    # Add legend
    legend_elements = [plt.Rectangle((0, 0), 1, 1, facecolor=color, label=state)
                      for state, color in state_colors.items()]
    ax1.legend(handles=legend_elements, loc='upper right', ncol=4)
    
    # Calculate burst lengths
    burst_lengths = []
    current_burst = 0
    for i in range(num_packets):
        if i in lost_packets:
            current_burst += 1
        elif current_burst > 0:
            burst_lengths.append(current_burst)
            current_burst = 0
    if current_burst > 0:
        burst_lengths.append(current_burst)
    
    # Plot burst length histogram
    if burst_lengths:
        max_burst = max(burst_lengths)
        bins = np.arange(1, max_burst + 2) - 0.5
        ax3.hist(burst_lengths, bins=bins, color='#4A90E2', edgecolor='black', 
                linewidth=0.5, density=True)
        ax3.set_title('Burst Length Distribution', fontsize=14)
        ax3.set_xlabel('Burst Length (packets)', fontsize=12)
        ax3.set_ylabel('Density', fontsize=12)
        
        # Add text with statistics
        mean_bll = np.mean(burst_lengths)
        loss_rate = len(lost_packets) / num_packets
        stats_text = f'Mean BLL: {mean_bll:.2f}\nLoss Rate: {loss_rate:.2%}'
        ax3.text(0.95, 0.95, stats_text, transform=ax3.transAxes, 
                ha='right', va='top', bbox=dict(facecolor='white', alpha=0.8))
    
    # Create 500x500 grid for packet visualization
    grid_size = 500
    packet_grid = np.zeros((grid_size, grid_size))
    
    # Fill the grid with packet data
    lost_set = set(lost_packets)
    for seq in range(min(num_packets, grid_size * grid_size)):
        i, j = divmod(seq, grid_size)
        if seq in lost_set:
            packet_grid[i][j] = 1
    
    # Plot the grid
    cmap = plt.cm.colors.ListedColormap(['#00b894', '#d63031'])  # Soft green and red
    im = ax2.imshow(packet_grid, cmap=cmap, interpolation='none', aspect='equal')
    ax2.set_title('Packet Loss Pattern (500x500 Grid)', fontsize=14)
    ax2.axis('off')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax2, ticks=[0, 1])
    cbar.set_ticklabels(['Delivered', 'Lost'])
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Configuration
    EMULATOR_PORT = 5000
    RECEIVER_PORT = 5001
    NUM_PACKETS = 250_000  # Changed to 1 million packets
    
    # Load delay config
    print("[Main] Loading delay configuration...")
    with open('./src/netfi/canonical_configs/delay_config.json', 'r') as f:
        delay_params = json.load(f)

    # Start Network Emulator
    print("[Main] Starting network emulator...")
    delay_emulator = DelayEmulator(
        input_port=EMULATOR_PORT,
        output_port=RECEIVER_PORT,
        network_type='4G',
        params=delay_params,
        protocol='udp'
    )
    
    # Start receiver first using ThreadWithReturn
    print("[Main] Starting receiver thread...")
    receiver_thread = ThreadWithReturn(
        target=packet_receiver,
        args=(RECEIVER_PORT, NUM_PACKETS)
    )
    receiver_thread.start()
    
    # Start emulator
    print("[Main] Starting emulator...")
    delay_emulator.start()
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
    
    delays = receiver_thread.join()  # Now this will properly return the delays dictionary
    print("[Main] Receiver thread completed")
    
    print("[Main] Stopping emulator...")
    delay_emulator.stop()
    print("[Main] Emulator stopped")
    
    # Analyze and visualize
    print("\n[Main] Analyzing results...")
    stats = analyze_delays(delays)
    print("\n[Main] Visualization:")
    visualize_results(stats)