import os
import csv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import struct
import lz4.frame

# Define the packet structure
fields = 'sequence pactyp version delx0 delx1 dely0 dely1 delz0 delz1 Qx0 Qx1 Qy0 Qy1 Qz0 Qz1 Qw0 Qw1 buttonstate0 buttonstate1 grasp0 grasp1 surgeon_mode checksum'.split()
format_str = '<IIIiiiiiiddddddddiiiiii'

def get_psm_vars(command, index):
    
    deltaX = command[f'delx{index}']
    deltaY = command[f'dely{index}']
    deltaZ = command[f'delz{index}']

    deltaQx = command[f'Qx{index}']
    deltaQy = command[f'Qy{index}']
    deltaQz = command[f'Qz{index}']

    grasp = command[f'grasp{index}']

    
    return ((deltaX, deltaY, deltaZ), (deltaQx, deltaQy, deltaQz), grasp)

def get_time_sequence_pedal_value(command):

    sequence = command[f'sequence']
    surgeon_mode = command[f'surgeon_mode'] 
    timestamp = command[f'timestamp']
    dropped = int(command[f'dropped'])

    return timestamp, sequence, surgeon_mode, dropped

def extract_packets_from_bin(bin_file, output_csv=None):
    """
    Extract packets from a binary file and save to CSV.
    
    Args:
        bin_file: Path to the binary file
        output_csv: Path to save the CSV output (if None, will create based on input filename)
    
    Returns:
        DataFrame containing extracted packet data
    """
    if output_csv is None:
        output_csv = os.path.join(os.path.dirname(bin_file), 'console_data_completed_1.csv')
        
    # Check file size
    size = os.path.getsize(bin_file)
    print(f"File size: {size} bytes")
    
    # Read first few bytes to check format
    with open(bin_file, "rb") as f:
        header = f.read(4)
    
    # Check if it's LZ4 frame format
    is_lz4 = header.startswith(b'\x04\x22\x4d\x18')
    print(f"Is LZ4 compressed: {is_lz4}")
    
    # Try to read and extract all packets
    packet_data_list = []
    
    try:
        if is_lz4:
            # LZ4 compressed file
            print("Reading LZ4 compressed file...")
            with lz4.frame.open(bin_file, 'rb') as f:
                process_packet_stream(f, packet_data_list)
        else:
            # Raw binary file
            print("Reading raw binary file...")
            with open(bin_file, 'rb') as f:
                process_packet_stream(f, packet_data_list)
    except Exception as e:
        print(f"Error reading file: {e}")
        return None
    
    print(f"Extracted {len(packet_data_list)} packets")
    
    # Convert to DataFrame
    if packet_data_list:
        df = pd.DataFrame(packet_data_list)
        
        # Save to CSV
        with open(output_csv, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["time_stamp", "sequence_number", "pos0_x", "pos0_y", "pos0_z", "rot0_x", "rot0_y", "rot0_z", 
                             "pos1_x", "pos1_y", "pos1_z", "rot1_x", "rot1_y", "rot1_z", "grasper0", "grasper1", "pedal", "drop"])
            for p in packet_data_list:
                pos0, rot0, grasp0 = get_psm_vars(p, 0)
                pos1, rot1, grasp1 = get_psm_vars(p, 1)
                ts, seq_num, pedal, drop = get_time_sequence_pedal_value(p)
                writer.writerow([ts, seq_num, *pos0, *rot0, *pos1, *rot1, grasp0, grasp1, pedal, drop])
        
        print(f"Data saved to {output_csv}")
        
        return df
    else:
        print("No packets extracted")
        return None

def process_packet_stream(file_obj, packet_data_list):
    """
    Process the packet stream from an open file.
    
    Args:
        file_obj: Open file object
        packet_data_list: List to append packet data to
    """
    packet_count = 0
    
    while True:
        try:
            # Read packet header
            header = file_obj.read(11)  # 8 bytes timestamp + 2 bytes length + 1 byte dropped flag
            if not header or len(header) < 11:
                break
                
            # Unpack the header
            timestamp, length, dropped = struct.unpack('!QH?', header)
            
            # Read packet data
            data = file_obj.read(length)
            if not data or len(data) < struct.calcsize(format_str):
                # Skip packets that don't match our expected format
                continue
                
            # Unpack the packet data
            try:
                unpacked = struct.unpack(format_str, data)
                packet_data = dict(zip(fields, unpacked))
                packet_data['timestamp'] = timestamp
                packet_data['dropped'] = dropped
                packet_data_list.append(packet_data)
                packet_count += 1
                
                # Print progress every 1000 packets
                if packet_count % 1000 == 0:
                    print(f"Processed {packet_count} packets...")
            except struct.error:
                # Handle packets with incorrect size
                print(f"Skipping packet with unexpected size: {len(data)} bytes")
                continue
                
        except EOFError:
            break
        except Exception as e:
            print(f"Error processing packet: {e}")
            break

def analyze_no_fault(scenario_dir, output_dir=None):
    """
    Analyze no_fault experiment data by comparing extracted packet data with received data.
    
    Args:
        scenario_dir: Path to the scenario directory
        output_dir: Directory to save results (if None, will use scenario_dir)
    
    Returns:
        Dictionary with analysis results
    """
    # Set output directory
    if output_dir is None:
        output_dir = scenario_dir
    os.makedirs(output_dir, exist_ok=True)
    
    # Define file paths
    emulator_bin = os.path.join(scenario_dir, 'console_data_complete_1.bin')
    extracted_csv = os.path.join(scenario_dir, 'console_data_completed_1.csv')
    received_csv = os.path.join(scenario_dir, 'console_data_recieved_1.csv')
    
    # Check if binary file exists
    if not os.path.exists(emulator_bin):
        print(f"Binary data file not found: {emulator_bin}")
        return {}
    
    # Extract packets from the binary file
    print(f"Extracting packets from binary file: {emulator_bin}")
    emulator_df = extract_packets_from_bin(emulator_bin, extracted_csv)
    
    if emulator_df is None or emulator_df.empty:
        print("Failed to extract packet data from binary file")
        return {}
    
    # Check if received data file exists
    if not os.path.exists(received_csv):
        print(f"Received data file not found: {received_csv}")
        return {}
    
    # Load received data
    print(f"Loading received data from {received_csv}")
    received_df = pd.read_csv(received_csv)
    
    print(f"Emulator data: {len(emulator_df)} rows")
    print(f"Received data: {len(received_df)} rows")
    
    # Extract relevant columns
    if 'sequence' not in emulator_df.columns:
        print("Error: 'sequence' column not found in emulator data")
        return {}
    
    if 'sequence_number' not in received_df.columns:
        print("Error: 'sequence_number' column not found in received data")
        return {}
    
    # Check for gaps in the sequence numbers of the extracted packets
    emulator_df = emulator_df.sort_values('sequence')
    sequence_numbers = emulator_df['sequence'].values
    
    # Calculate the expected consecutive sequence numbers
    min_seq = sequence_numbers.min()
    max_seq = sequence_numbers.max()
    expected_sequence = set(range(min_seq, max_seq + 1))
    actual_sequence = set(sequence_numbers)
    
    # Find the missing sequence numbers (gaps)
    sequence_gaps = expected_sequence - actual_sequence
    
    # Calculate the packet loss rate due to gaps
    total_expected_packets = len(expected_sequence)
    gap_losses = len(sequence_gaps)
    gap_loss_rate = gap_losses / total_expected_packets if total_expected_packets > 0 else 0
    
    print(f"\nAnalysis of gaps in extracted packets:")
    print(f"Minimum sequence: {min_seq}")
    print(f"Maximum sequence: {max_seq}")
    print(f"Expected consecutive packets: {total_expected_packets}")
    print(f"Actual extracted packets: {len(actual_sequence)}")
    print(f"Missing packets (gaps): {gap_losses}")
    print(f"Packet loss rate due to gaps: {gap_loss_rate * 100:.2f}%")
    
    # Find consecutive missing packets in gaps (bursts)
    if sequence_gaps:
        gaps_list = sorted(list(sequence_gaps))
        gap_burst_lengths = []
        current_burst = 1
        
        for i in range(1, len(gaps_list)):
            if gaps_list[i] == gaps_list[i-1] + 1:
                current_burst += 1
            else:
                gap_burst_lengths.append(current_burst)
                current_burst = 1
        
        # Add the last burst
        if current_burst > 0:
            gap_burst_lengths.append(current_burst)
        
        # Calculate burst statistics for gaps
        gap_burst_stats = {
            'mean': np.mean(gap_burst_lengths),
            'median': np.median(gap_burst_lengths),
            'std': np.std(gap_burst_lengths),
            'min': min(gap_burst_lengths),
            'max': max(gap_burst_lengths),
            'total_bursts': len(gap_burst_lengths),
            'burst_lengths': gap_burst_lengths
        }
        
        print(f"Gap burst statistics:")
        print(f"Total bursts: {gap_burst_stats['total_bursts']}")
        print(f"Mean burst length: {gap_burst_stats['mean']:.2f}")
        print(f"Median burst length: {gap_burst_stats['median']:.2f}")
        print(f"Max burst length: {gap_burst_stats['max']}")
    else:
        gap_burst_stats = {
            'mean': 0,
            'median': 0,
            'std': 0,
            'min': 0,
            'max': 0,
            'total_bursts': 0,
            'burst_lengths': []
        }
        print("No gaps found in sequence numbers")

    # Find the minimum sequence number in the received data
    min_received_sequence = received_df['sequence_number'].min()
    print(f"\nMinimum sequence number in received data: {min_received_sequence}")
    
    # Filter out emulator packets with sequence numbers smaller than the minimum received sequence
    filtered_emulator_df = emulator_df[emulator_df['sequence'] >= min_received_sequence].copy()
    print(f"Filtered emulator data: {len(filtered_emulator_df)} rows (removed {len(emulator_df) - len(filtered_emulator_df)} rows)")
    
    # Convert timestamp in emulator data from nanoseconds to seconds
    if 'timestamp' in filtered_emulator_df.columns:
        filtered_emulator_df['emulator_timestamp'] = filtered_emulator_df['timestamp'] / 1e9
    else:
        print("Error: 'timestamp' column not found in emulator data")
        return {}
    
    if 'time_stamp' not in received_df.columns:
        print("Error: 'time_stamp' column not found in received data")
        return {}
    
    # Rename for clarity
    received_df['received_timestamp'] = received_df['time_stamp']
    
    # Analyze packet loss
    # Get all sequence numbers from emulator and received data
    emulator_sequences = set(filtered_emulator_df['sequence'].values)
    received_sequences = set(received_df['sequence_number'].values)
    
    # Find missing packets (sent by emulator but not received)
    missing_sequences = emulator_sequences - received_sequences
    
    # Calculate packet loss
    total_packets = len(emulator_sequences)
    lost_packets = len(missing_sequences)
    loss_rate = lost_packets / total_packets if total_packets > 0 else 0
    
    print(f"\nAnalysis of packets missing at receiver:")
    print(f"Total packets sent (after filtering): {total_packets}")
    print(f"Packets lost: {lost_packets}")
    print(f"Packet loss rate: {loss_rate * 100:.2f}%")
    
    # Find consecutive lost packets (bursts)
    if missing_sequences:
        missing_list = sorted(list(missing_sequences))
        burst_lengths = []
        current_burst = 1
        
        for i in range(1, len(missing_list)):
            if missing_list[i] == missing_list[i-1] + 1:
                current_burst += 1
            else:
                burst_lengths.append(current_burst)
                current_burst = 1
        
        # Add the last burst
        if current_burst > 0:
            burst_lengths.append(current_burst)
        
        # Calculate burst statistics
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
    
    # Analyze delay
    # Merge the dataframes on sequence number
    merged_df = pd.merge(
        filtered_emulator_df[['sequence', 'emulator_timestamp']],
        received_df[['sequence_number', 'received_timestamp']],
        left_on='sequence', 
        right_on='sequence_number',
        how='inner'
    )
    
    # Calculate delay (received - emulator)
    merged_df['delay'] = merged_df['received_timestamp'] - merged_df['emulator_timestamp']
    
    # Convert to milliseconds for reporting
    merged_df['delay_ms'] = merged_df['delay'] * 1000.0
    
    # Calculate delay statistics
    if not merged_df.empty:
        delay_stats = {
            'mean_delay': np.mean(merged_df['delay_ms']),
            'median_delay': np.median(merged_df['delay_ms']),
            'std_delay': np.std(merged_df['delay_ms']),
            'min_delay': np.min(merged_df['delay_ms']),
            'max_delay': np.max(merged_df['delay_ms']),
            'p95_delay': np.percentile(merged_df['delay_ms'], 95),
            'p99_delay': np.percentile(merged_df['delay_ms'], 99),
            'delays': merged_df['delay_ms'].tolist()
        }
    else:
        delay_stats = {
            'mean_delay': 0,
            'median_delay': 0,
            'std_delay': 0,
            'min_delay': 0,
            'max_delay': 0,
            'p95_delay': 0,
            'p99_delay': 0,
            'delays': []
        }
    
    # Create plots
    create_analysis_plots(total_packets, lost_packets, loss_rate,
                         burst_stats, delay_stats,
                         os.path.join(output_dir, 'no_fault_analysis'),
                         gap_losses, gap_loss_rate, gap_burst_stats)
    
    # Save results to CSV
    save_results_to_csv(merged_df, missing_sequences, burst_stats, delay_stats, 
                       output_dir, sequence_gaps, gap_burst_stats)
    
    # Combine all results
    results = {
        'total_packets': total_packets,
        'lost_packets': lost_packets,
        'loss_rate': loss_rate,
        'burst_stats': burst_stats,
        'gap_losses': gap_losses,
        'gap_loss_rate': gap_loss_rate,
        'gap_burst_stats': gap_burst_stats,
        **delay_stats
    }
    
    return results

def create_analysis_plots(total_packets, lost_packets, loss_rate, burst_stats, delay_stats, output_prefix, gap_losses=0, gap_loss_rate=0, gap_burst_stats=None):
    """
    Create plots for the no_fault analysis.
    
    Args:
        total_packets: Total number of packets
        lost_packets: Number of lost packets
        loss_rate: Packet loss rate
        burst_stats: Dictionary with burst statistics
        delay_stats: Dictionary with delay statistics
        output_prefix: Prefix for output files
        gap_losses: Number of packet losses due to gaps in sequence numbers
        gap_loss_rate: Packet loss rate due to gaps
        gap_burst_stats: Dictionary with burst statistics for gaps
    """
    # Create packet loss plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title('Packet Loss Analysis')
    ax.text(0.5, 0.5, f"Total Packets: {total_packets}\n"
                      f"Packets Lost at Receiver: {lost_packets}\n"
                      f"Loss Rate at Receiver: {loss_rate * 100:.2f}%\n"
                      f"Packet Losses due to Gaps: {gap_losses}\n"
                      f"Gap Loss Rate: {gap_loss_rate * 100:.2f}%\n"
                      f"Total Bursts: {burst_stats['total_bursts']}\n"
                      f"Mean Burst Length: {burst_stats['mean']:.2f}\n"
                      f"Max Burst Length: {burst_stats['max']:.2f}",
             horizontalalignment='center',
             verticalalignment='center',
             transform=ax.transAxes,
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
             fontsize=12)
    ax.set_axis_off()
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_packet_loss.png")
    plt.close()
    
    # Create burst length histogram if there are any bursts
    if burst_stats['burst_lengths']:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_title('Burst Length Distribution')
        ax.set_xlabel('Burst Length')
        ax.set_ylabel('Count')
        ax.hist(burst_stats['burst_lengths'], bins=min(30, max(5, burst_stats['total_bursts'])), alpha=0.7)
        ax.axvline(burst_stats['mean'], color='r', linestyle='--', 
                   label=f'Mean: {burst_stats["mean"]:.2f}')
        ax.axvline(burst_stats['median'], color='g', linestyle='--',
                   label=f'Median: {burst_stats["median"]:.2f}')
        ax.legend()
        plt.tight_layout()
        plt.savefig(f"{output_prefix}_burst_distribution.png")
        plt.close()
    
    # Create delay distribution histogram
    if delay_stats['delays']:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_title('Delay Distribution')
        ax.set_xlabel('Delay (ms)')
        ax.set_ylabel('Count')
        ax.hist(delay_stats['delays'], bins=50, alpha=0.7)
        ax.axvline(delay_stats['mean_delay'], color='r', linestyle='--',
                   label=f'Mean: {delay_stats["mean_delay"]:.2f} ms')
        ax.axvline(delay_stats['median_delay'], color='g', linestyle='--',
                   label=f'Median: {delay_stats["median_delay"]:.2f} ms')
        ax.legend()
        plt.tight_layout()
        plt.savefig(f"{output_prefix}_delay_distribution.png")
        plt.close()
        
        # Create delay over time plot
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.set_title('Delay over Packet Sequence')
        ax.set_xlabel('Packet Index')
        ax.set_ylabel('Delay (ms)')
        ax.plot(delay_stats['delays'], 'b-', linewidth=0.5, alpha=0.7)
        ax.axhline(y=delay_stats['mean_delay'], color='r', linestyle='--', 
                   label=f'Mean: {delay_stats["mean_delay"]:.2f} ms')
        ax.legend()
        plt.tight_layout()
        plt.savefig(f"{output_prefix}_delay_time_series.png")
        plt.close()

def save_results_to_csv(merged_df, missing_sequences, burst_stats, delay_stats, output_dir, sequence_gaps=None, gap_burst_stats=None):
    """
    Save analysis results to CSV files.
    
    Args:
        merged_df: DataFrame with merged emulator and received data
        missing_sequences: Set of missing sequence numbers
        burst_stats: Dictionary with burst statistics
        delay_stats: Dictionary with delay statistics
        output_dir: Directory to save results
        sequence_gaps: Set of sequence gaps detected in the emulator data
        gap_burst_stats: Dictionary with burst statistics for gaps
    """
    # Save delay data
    if not merged_df.empty:
        delay_file = os.path.join(output_dir, 'delay_analysis.csv')
        merged_df[['sequence', 'emulator_timestamp', 'received_timestamp', 'delay_ms']].to_csv(
            delay_file, index=False)
        print(f"Delay analysis saved to {delay_file}")
    
    # Save missing sequences
    if missing_sequences:
        missing_file = os.path.join(output_dir, 'missing_sequences.csv')
        pd.DataFrame({'sequence': sorted(list(missing_sequences))}).to_csv(
            missing_file, index=False)
        print(f"Missing sequences saved to {missing_file}")
    
    # Save sequence gaps
    if sequence_gaps and len(sequence_gaps) > 0:
        gaps_file = os.path.join(output_dir, 'sequence_gaps.csv')
        pd.DataFrame({'sequence_gap': sorted(list(sequence_gaps))}).to_csv(
            gaps_file, index=False)
        print(f"Sequence gaps saved to {gaps_file}")
    
    # Save burst statistics
    if burst_stats['burst_lengths']:
        burst_file = os.path.join(output_dir, 'burst_analysis.csv')
        pd.DataFrame({'burst_length': burst_stats['burst_lengths']}).to_csv(
            burst_file, index=False)
        print(f"Burst analysis saved to {burst_file}")
    
    # Save gap burst statistics
    if gap_burst_stats and gap_burst_stats['burst_lengths']:
        gap_burst_file = os.path.join(output_dir, 'gap_burst_analysis.csv')
        pd.DataFrame({'gap_burst_length': gap_burst_stats['burst_lengths']}).to_csv(
            gap_burst_file, index=False)
        print(f"Gap burst analysis saved to {gap_burst_file}")
    
    # Save summary statistics
    summary_file = os.path.join(output_dir, 'analysis_summary.csv')
    
    # Calculate gap statistics
    gap_count = len(sequence_gaps) if sequence_gaps else 0
    gap_rate = gap_count / (len(merged_df) + gap_count) if (len(merged_df) + gap_count) > 0 else 0
    
    summary_df = pd.DataFrame([{
        'total_packets': len(merged_df) + len(missing_sequences),
        'received_packets': len(merged_df),
        'lost_packets': len(missing_sequences),
        'loss_rate': len(missing_sequences) / (len(merged_df) + len(missing_sequences)) if (len(merged_df) + len(missing_sequences)) > 0 else 0,
        'total_bursts': burst_stats['total_bursts'],
        'mean_burst_length': burst_stats['mean'],
        'median_burst_length': burst_stats['median'],
        'max_burst_length': burst_stats['max'],
        'gap_packets': gap_count,
        'gap_rate': gap_rate,
        'gap_bursts': gap_burst_stats['total_bursts'] if gap_burst_stats else 0,
        'mean_gap_burst_length': gap_burst_stats['mean'] if gap_burst_stats else 0,
        'max_gap_burst_length': gap_burst_stats['max'] if gap_burst_stats else 0,
        'mean_delay_ms': delay_stats['mean_delay'],
        'median_delay_ms': delay_stats['median_delay'],
        'min_delay_ms': delay_stats['min_delay'],
        'max_delay_ms': delay_stats['max_delay'],
        'p95_delay_ms': delay_stats['p95_delay'],
        'p99_delay_ms': delay_stats['p99_delay']
    }])
    summary_df.to_csv(summary_file, index=False)
    print(f"Summary statistics saved to {summary_file}")

def process_all_scenarios(experiment_dir, output_dir=None):
    """
    Process all no_fault scenarios in the experiment directory.
    
    Args:
        experiment_dir: Path to the experiment directory
        output_dir: Directory to save results (if None, will use experiment_dir)
    """
    if output_dir is None:
        output_dir = experiment_dir
    
    no_fault_dir = os.path.join(experiment_dir, 'no_fault')
    if not os.path.exists(no_fault_dir):
        print(f"No fault directory not found: {no_fault_dir}")
        return
    
    # Process each scenario
    results = {}
    for scenario in os.listdir(no_fault_dir):
        scenario_dir = os.path.join(no_fault_dir, scenario)
        if not os.path.isdir(scenario_dir):
            continue
        
        print(f"\nProcessing scenario: {scenario}")
        scenario_output_dir = os.path.join(output_dir, scenario)
        os.makedirs(scenario_output_dir, exist_ok=True)
        
        result = analyze_no_fault(scenario_dir, scenario_output_dir)
        results[scenario] = result
    
    return results

if __name__ == "__main__":
    import sys
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze no-fault experiment data.')
    parser.add_argument('--scenario_dir', help='Path to the scenario directory')
    parser.add_argument('--output_dir', help='Directory to save results')
    
    args = parser.parse_args()
    
    if args.scenario_dir:
        experiment_dir = args.scenario_dir
    else:
        experiment_dir = "exp_data_1"
        
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = "no_fault_results"
    
    # Process all scenarios
    process_all_scenarios(experiment_dir, output_dir) 