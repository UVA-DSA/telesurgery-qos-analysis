import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from netfi.emulators.packet_reorder_emulator import PacketReorderEmulator
import threading
import time
import socket
import struct
import random
import string
from collections import defaultdict
import json

from test_utils import ThreadWithReturn

def generate_random_payload(length=32):
    """Generate random string payload"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length)).encode()


def packet_sender(host: str, port: int, num_packets: int):
    """Send UDP packets with sequence numbers"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[Sender] Starting to send {num_packets} packets...")
    start_time = time.time()
    
    for i in range(num_packets):
        payload = generate_random_payload()
        # Pack sequence number (I) and payload
        data = struct.pack(f'!I{len(payload)}s', i, payload)
        sock.sendto(data, (host, port))
        
        if i % 1000 == 0 and i > 0:
            print(f"[Sender] Sent {i}/{num_packets} packets ({i/num_packets:.0%})")
    
    sock.close()
    duration = time.time() - start_time
    print(f"[Sender] Completed in {duration:.2f}s ({num_packets/duration:.0f} pkt/s)")

def packet_receiver(port: int, num_packets: int):
    """Receive UDP packets and track their order"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', port))
    sock.settimeout(5)  # Set receive timeout to 5 seconds
    
    received_order = {}  # {sequence_number: received_order}
    receive_counter = 0
    print(f"[Receiver] Listening on port {port} for {num_packets} packets...")
    start_time = time.time()
    last_print = 0
    last_received = 0
    timeout_counter = 0
    
    while len(received_order) < num_packets and timeout_counter < 3:
        try:
            data, _ = sock.recvfrom(4096)
            seq = struct.unpack('!I', data[:4])[0]
            received_order[seq] = receive_counter
            receive_counter += 1
            
            last_received = time.time()
            timeout_counter = 0
            
            if time.time() - last_print > 2:
                print(f"[Receiver] Received {len(received_order)}/{num_packets} packets ({len(received_order)/num_packets:.0%})")
                last_print = time.time()
        
        except socket.timeout:
            if time.time() - last_received > 10:
                timeout_counter += 1
                print(f"[Receiver] Timeout {timeout_counter}/3 - No packets received for 10 seconds")
            continue
    
    sock.close()
    duration = time.time() - start_time
    print(f"[Receiver] Completed in {duration:.2f}s ({len(received_order)/duration:.0f} pkt/s)")
    return received_order

def analyze_reordering(received_order):
    """Analyze packet reordering patterns"""
    print("[Analyzer] Computing reordering statistics...")
    reorder_numbers = []
    
    for seq in range(len(received_order)):
        reorder_number = abs(seq - received_order[seq])
        reorder_numbers.append(reorder_number)
    
    stats = {
        'total_packets': len(received_order),
        'max_reorder': max(reorder_numbers),
        'min_reorder': min(reorder_numbers),
        'mean_reorder': np.mean(reorder_numbers),
        'median_reorder': np.median(reorder_numbers),
        'std_reorder': np.std(reorder_numbers),
        'p95_reorder': np.percentile(reorder_numbers, 95),
        'reorder_numbers': reorder_numbers,
        'ordered_packets': sum(1 for r in reorder_numbers if r == 0),
    }
    return stats

def visualize_results(stats):
    """Create visualization of reordering statistics"""
    print("[Visualization] Generating plots...")
    plt.style.use('ggplot')
    fig = plt.figure(figsize=(20, 10))
    
    # Create grid layout
    gs = fig.add_gridspec(2, 3, width_ratios=[1, 1.5, 0.5])
    
    # Reorder Number Distribution Histogram
    ax1 = fig.add_subplot(gs[0, 0])
    sns.histplot(data=stats['reorder_numbers'], bins=50, ax=ax1,
                color='#2e86de', edgecolor='#1a3c6d')
    ax1.set_title('Reorder Number Distribution', fontsize=14, pad=20)
    ax1.set_xlabel('Reorder Number', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    
    # Reorder Pattern Heatmap
    ax2 = fig.add_subplot(gs[:, 1])
    grid_size = int(np.ceil(np.sqrt(stats['total_packets'])))
    reorder_grid = np.zeros((grid_size, grid_size))
    
    print("[Visualization] Creating reorder grid...")
    for i, reorder in enumerate(stats['reorder_numbers']):
        if i >= stats['total_packets']:
            break
        row = i // grid_size
        col = i % grid_size
        reorder_grid[row][col] = reorder
    
    print("[Visualization] Generating heatmap...")
    heatmap = sns.heatmap(reorder_grid, cmap='YlOrRd', ax=ax2,
                         xticklabels=False, yticklabels=False)
    colorbar = heatmap.collections[0].colorbar
    colorbar.set_label('Reorder Number', fontsize=10)
    ax2.set_title('Packet Reordering Pattern', fontsize=14, pad=20)
    
    # Statistics Panel
    ax3 = fig.add_subplot(gs[:, 2])
    ax3.axis('off')
    
    stats_text = [
        "Packet Reordering Statistics",
        "─" * 25,
        f"Total Packets: {stats['total_packets']:,}",
        f"Ordered Packets: {stats['ordered_packets']:,}",
        f"Ordered Ratio: {stats['ordered_packets']/stats['total_packets']:.1%}",
        f"Min Reorder: {stats['min_reorder']:.0f}",
        f"Max Reorder: {stats['max_reorder']:.0f}",
        f"Mean Reorder: {stats['mean_reorder']:.2f}",
        f"Median Reorder: {stats['median_reorder']:.0f}",
        f"Std Dev: {stats['std_reorder']:.2f}",
        f"95th Percentile: {stats['p95_reorder']:.0f}"
    ]
    
    ax3.text(0.1, 0.7, "\n".join(stats_text),
            fontsize=12, linespacing=1.8,
            color='#2d3436', fontfamily='monospace',
            bbox=dict(facecolor='#f8f9fa', edgecolor='#dfe6e9',
                    boxstyle='round,pad=1'))
    
    # Add CDF plot
    ax4 = fig.add_subplot(gs[1, 0])
    sorted_reorders = np.sort(stats['reorder_numbers'])
    cumulative = np.arange(1, len(sorted_reorders) + 1) / len(sorted_reorders)
    ax4.plot(sorted_reorders, cumulative, color='#2e86de', linewidth=2)
    ax4.set_title('Cumulative Distribution Function', fontsize=14, pad=20)
    ax4.set_xlabel('Reorder Number', fontsize=12)
    ax4.set_ylabel('Cumulative Probability', fontsize=12)
    ax4.grid(True)
    
    plt.suptitle("Packet Reordering Analysis",
                fontsize=18, y=0.98,
                color='#2d3436', fontweight='bold')
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()
    print("[Visualization] Displaying results window")

if __name__ == "__main__":
    # Configuration
    EMULATOR_PORT = 5000
    RECEIVER_PORT = 5001
    NUM_PACKETS = 10_000
    # Load parameters from config file
    with open('./src/netfi/canonical_configs/packet_reorder_config.json') as f:
        PARAMS = json.load(f)

    # Start Network Emulator
    print("[Main] Starting network emulator...")
    reorder_emulator = PacketReorderEmulator(
        input_port=EMULATOR_PORT,
        output_port=RECEIVER_PORT,
        params=PARAMS,
        protocol='udp',
        wait_for_full_queue=False
    )
    

    # Start receiver first
    print("[Main] Starting receiver thread...")
    receiver_thread = ThreadWithReturn(
        target=packet_receiver,
        args=(RECEIVER_PORT, NUM_PACKETS)
    )
    receiver_thread.start()
    
    # Start emulator
    print("[Main] Starting emulator...")
    reorder_emulator.start()
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
    
    received_order = receiver_thread.join()
    print("[Main] Receiver thread completed")
    
    print("[Main] Stopping emulator...")
    reorder_emulator.stop()
    print("[Main] Emulator stopped")
    
    # Analyze and visualize
    print("\n[Main] Analyzing results...")
    stats = analyze_reordering(received_order)
    print("\n[Main] Visualization:")
    visualize_results(stats)
