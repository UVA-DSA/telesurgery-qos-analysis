import numpy as np
import matplotlib.pyplot as plt
import lz4.frame
import struct
import os
from typing import Dict, List, Tuple
import pandas as pd
from collections import namedtuple

fields = 'sequence pactyp version delx0 delx1 dely0 dely1 delz0 delz1 Qx0 Qx1 Qy0 Qy1 Qz0 Qz1 Qw0 Qw1 buttonstate0 buttonstate1 grasp0 grasp1 surgeon_mode checksum'.split()
UStruct = namedtuple('UStruct', fields)
format_str = '<IIIiiiiiiddddddddiiiiii'




def read_packet_log(log_file: str) -> Tuple[List[int], List[bool], List[Dict]]:
    """
    Read a packet log file and extract sequence numbers, loss flags, and packet data.
    
    Args:
        log_file: Path to the .bin log file
        
    Returns:
        Tuple of (sequence numbers, loss flags, packet data)
    """
    sequence_numbers = []
    loss_flags = []
    packet_data_list = []
    
    try:
        with lz4.frame.open(log_file, 'rb') as f:
            while True:
                # Read header (timestamp, length, dropped flag)
                header = f.read(11)  # 8 bytes timestamp + 4 bytes length + 1 byte dropped flag
                if not header:
                    break
                    
                # Unpack the header
                # Format: !QH? where:
                # Q: unsigned long long (8 bytes) for timestamp
                # H: unsigned short (2 bytes) for length
                # ?: bool (1 byte) for dropped flag
                timestamp, length, dropped = struct.unpack('!QH?', header)
                
                # Read packet data
                data = f.read(length)
                if len(data) == struct.calcsize(format_str):
                    unpacked = struct.unpack(format_str, data)
                    packet_data = UStruct._make(unpacked)._asdict()
                    packet_data['timestamp'] = timestamp
                    packet_data['dropped'] = dropped
                else:
                    # Handle case where data doesn't match expected format
                    packet_data = {'timestamp': timestamp, 'dropped': dropped}
                
                # Store sequence number, loss flag, and packet data
                sequence_numbers.append(len(sequence_numbers))  # Use index as sequence number
                loss_flags.append(dropped)
                packet_data_list.append(packet_data)
                
    except FileNotFoundError:
        print(f"Error: Log file {log_file} not found")
        return [], [], []
    except Exception as e:
        print(f"Error reading log file: {e}")
        return [], [], []
    
    return sequence_numbers, loss_flags, packet_data_list

def calculate_burst_lengths(loss_flags: List[bool]) -> List[int]:
    """
    Calculate the lengths of loss bursts from loss flags.
    
    Args:
        loss_flags: List of boolean flags indicating lost packets
        
    Returns:
        List of burst lengths
    """
    burst_lengths = []
    current_burst = 0
    
    for lost in loss_flags:
        if lost:
            current_burst += 1
        elif current_burst > 0:
            burst_lengths.append(current_burst)
            current_burst = 0
    
    # Handle case where log ends during a burst
    if current_burst > 0:
        burst_lengths.append(current_burst)
    
    return burst_lengths

def analyze_packet_loss(log_file: str) -> Dict:
    """
    Analyze packet loss patterns from a log file.
    
    Args:
        log_file: Path to the .bin log file
        
    Returns:
        Dictionary containing analysis results
    """
    # Read the log file
    sequence_numbers, loss_flags, packet_data_list = read_packet_log(log_file)
    
    if not sequence_numbers:
        return {}
    
    # Calculate overall loss rate
    total_packets = len(sequence_numbers)
    lost_packets = sum(loss_flags)
    loss_rate = lost_packets / total_packets
    
    # Calculate burst lengths
    burst_lengths = calculate_burst_lengths(loss_flags)
    
    # Calculate burst statistics
    if burst_lengths:
        burst_stats = {
            'mean': np.mean(burst_lengths),
            'median': np.median(burst_lengths),
            'std': np.std(burst_lengths),
            'min': min(burst_lengths),
            'max': max(burst_lengths),
            'total_bursts': len(burst_lengths),
            'burst_lengths': burst_lengths
        }
    else:
        burst_stats = {
            'mean': 0,
            'median': 0,
            'std': 0,
            'min': 0,
            'max': 0,
            'total_bursts': 0,
            'burst_lengths': []
        }
    
    return {
        'total_packets': total_packets,
        'lost_packets': lost_packets,
        'loss_rate': loss_rate,
        'burst_stats': burst_stats
    }

def plot_analysis(results: Dict, log_file: str):
    """
    Create plots of the analysis results.
    
    Args:
        results: Dictionary containing analysis results
        log_file: Path to the log file (used for plot title)
    """
    if not results:
        return
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot 1: Loss pattern
    ax1.set_title(f'Packet Loss Pattern - {os.path.basename(log_file)}')
    ax1.set_xlabel('Packet Number')
    ax1.set_ylabel('Lost')
    
    # Create a binary array for lost packets
    lost_mask = np.zeros(results['total_packets'], dtype=bool)
    lost_mask[:results['lost_packets']] = True  # Simplified visualization
    
    # Plot as a thin line
    ax1.plot(range(results['total_packets']), lost_mask, 'r-', linewidth=0.5)
    ax1.set_ylim(-0.1, 1.1)
    ax1.set_yticks([0, 1])
    ax1.set_yticklabels(['Received', 'Lost'])
    
    # Plot 2: Burst length histogram
    if results['burst_stats']['burst_lengths']:
        ax2.hist(results['burst_stats']['burst_lengths'], 
                bins=min(50, max(results['burst_stats']['burst_lengths'])),
                color='skyblue', edgecolor='black', linewidth=0.5, density=True)
        ax2.set_title('Burst Length Distribution')
        ax2.set_xlabel('Burst Length (packets)')
        ax2.set_ylabel('Density')
        
        # Add text with statistics
        stats_text = (f'Mean: {results["burst_stats"]["mean"]:.2f}\n'
                     f'Median: {results["burst_stats"]["median"]:.2f}\n'
                     f'Std: {results["burst_stats"]["std"]:.2f}\n'
                     f'Min: {results["burst_stats"]["min"]}\n'
                     f'Max: {results["burst_stats"]["max"]}\n'
                     f'Total Bursts: {results["burst_stats"]["total_bursts"]}\n'
                     f'Loss Rate: {results["loss_rate"]:.2%}')
        ax2.text(0.95, 0.95, stats_text, transform=ax2.transAxes, 
                ha='right', va='top', bbox=dict(facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.show()

def save_results_to_excel(results: Dict, log_file: str, output_file: str = None):
    """
    Save analysis results to an Excel file.
    
    Args:
        results: Dictionary containing analysis results
        log_file: Path to the log file
        output_file: Path to save the Excel file (optional)
    """
    if not results:
        return
    
    if output_file is None:
        output_file = f"{os.path.splitext(log_file)[0]}_analysis.xlsx"
    
    # Create DataFrame with overall statistics
    overall_stats = pd.DataFrame([{
        'Log File': os.path.basename(log_file),
        'Total Packets': results['total_packets'],
        'Lost Packets': results['lost_packets'],
        'Loss Rate': results['loss_rate'],
        'Total Bursts': results['burst_stats']['total_bursts'],
        'Mean Burst Length': results['burst_stats']['mean'],
        'Median Burst Length': results['burst_stats']['median'],
        'Std Burst Length': results['burst_stats']['std'],
        'Min Burst Length': results['burst_stats']['min'],
        'Max Burst Length': results['burst_stats']['max']
    }])
    
    # Create DataFrame with burst lengths
    burst_lengths = pd.DataFrame({
        'Burst Length': results['burst_stats']['burst_lengths']
    })
    
    # Save to Excel with multiple sheets
    with pd.ExcelWriter(output_file) as writer:
        overall_stats.to_excel(writer, sheet_name='Overall Statistics', index=False)
        burst_lengths.to_excel(writer, sheet_name='Burst Lengths', index=False)
    
    print(f"\nResults saved to {output_file}")

def save_packet_data_to_csv(packet_data_list: List[Dict], log_file: str, output_file: str = None):
    """
    Save packet data to a CSV file.
    
    Args:
        packet_data_list: List of dictionaries containing packet data
        log_file: Path to the log file
        output_file: Path to save the CSV file (optional)
    """
    if not packet_data_list:
        return
    
    if output_file is None:
        output_file = f"{os.path.splitext(log_file)[0]}_packets.csv"
    
    # Convert to DataFrame and save to CSV
    df = pd.DataFrame(packet_data_list)
    df.to_csv(output_file, index=False)
    print(f"\nPacket data saved to {output_file}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze packet loss patterns from a log file.')
    parser.add_argument('--log_file', help='Path to the .bin log file')
    parser.add_argument('--output', help='Path to save the Excel file (optional)')
    parser.add_argument('--csv_output', help='Path to save the CSV file (optional)')
    args = parser.parse_args()
    
    # Read the log file
    sequence_numbers, loss_flags, packet_data_list = read_packet_log(args.log_file)
    
    if sequence_numbers:
        # Save packet data to CSV
        save_packet_data_to_csv(packet_data_list, args.log_file, args.csv_output)
        
        # Analyze the log file
        results = analyze_packet_loss(args.log_file)
        
        if results:
            # Print summary
            print("\nPacket Loss Analysis Summary:")
            print(f"Total Packets: {results['total_packets']}")
            print(f"Lost Packets: {results['lost_packets']}")
            print(f"Loss Rate: {results['loss_rate']:.2%}")
            print(f"Total Bursts: {results['burst_stats']['total_bursts']}")
            print(f"Mean Burst Length: {results['burst_stats']['mean']:.2f}")
            print(f"Median Burst Length: {results['burst_stats']['median']:.2f}")
            print(f"Std Burst Length: {results['burst_stats']['std']:.2f}")
            print(f"Min Burst Length: {results['burst_stats']['min']}")
            print(f"Max Burst Length: {results['burst_stats']['max']}")
            
            # Create plots
            plot_analysis(results, args.log_file)
            
            # Save results to Excel
            save_results_to_excel(results, args.log_file, args.output)
    else:
        print("No data to analyze.") 