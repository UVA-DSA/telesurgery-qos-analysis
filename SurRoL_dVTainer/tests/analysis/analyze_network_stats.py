import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import struct
import lz4.frame
import os
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import namedtuple

# Define the packet structure
fields = 'sequence pactyp version delx0 delx1 dely0 dely1 delz0 delz1 Qx0 Qx1 Qy0 Qy1 Qz0 Qz1 Qw0 Qw1 buttonstate0 buttonstate1 grasp0 grasp1 surgeon_mode checksum'.split()
UStruct = namedtuple('UStruct', fields)
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


def read_packet_log(log_file: str, is_delay: bool = False) -> Tuple[List[int], List[bool], List[Dict]]:
    """
    Read a packet log file and extract sequence numbers, loss flags, and packet data.
    
    Args:
        log_file: Path to the .bin log file
        is_delay: Whether this is a delay emulator log file
        
    Returns:
        Tuple of (sequence numbers, loss flags, packet data)
    """
    sequence_numbers = []
    loss_flags = []
    packet_data_list = []
    
    try:
        with lz4.frame.open(log_file, 'rb') as f:
            while True:
                if is_delay:
                    # Read header (timestamp, length, delay)
                    header = f.read(14)  # 8 bytes timestamp + 2 bytes length + 4 bytes delay
                    if not header:
                        break
                    
                    # Unpack the header
                    timestamp, length, delay = struct.unpack('!QHf', header)
                    dropped = False  # Delay emulator doesn't drop packets
                else:
                    # Read header (timestamp, length, dropped flag)
                    header = f.read(11)  # 8 bytes timestamp + 2 bytes length + 1 byte dropped flag
                    if not header:
                        break
                    
                    # Unpack the header
                    timestamp, length, dropped = struct.unpack('!QH?', header)
                    delay = 0.0  # Packet loss emulator doesn't have delay
                
                # Read packet data
                data = f.read(length)
                if len(data) == struct.calcsize(format_str):
                    unpacked = struct.unpack(format_str, data)
                    packet_data = UStruct._make(unpacked)._asdict()
                    packet_data['timestamp'] = timestamp
                    packet_data['dropped'] = dropped
                    if is_delay:
                        packet_data['delay'] = delay * 1000  # Convert seconds to milliseconds
                else:
                    # Handle case where data doesn't match expected format
                    packet_data = {'timestamp': timestamp, 'dropped': dropped}
                    if is_delay:
                        packet_data['delay'] = delay * 1000  # Convert seconds to milliseconds
                
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

def analyze_packet_loss(sequence_numbers: List[int], loss_flags: List[bool]) -> Dict:
    """
    Analyze packet loss patterns.
    
    Args:
        sequence_numbers: List of sequence numbers
        loss_flags: List of boolean flags indicating lost packets
        
    Returns:
        Dictionary containing analysis results
    """
    if not sequence_numbers:
        return {}
    
    # Calculate overall loss rate
    total_packets = len(sequence_numbers)
    lost_packets = sum(loss_flags)
    loss_rate = lost_packets / total_packets
    
    # Calculate burst lengths
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

def analyze_delay(emulator_data: List[Dict], received_data: pd.DataFrame) -> Dict:
    """
    Analyze delay patterns by comparing emulator data with received data.
    
    Args:
        emulator_data: List of dictionaries containing packet data from emulator
        received_data: DataFrame containing received packet data
        
    Returns:
        Dictionary containing delay analysis results
    """
    if not emulator_data or received_data.empty:
        print("Warning: Empty emulator data or received data")
        return {
            'mean_error': 0,
            'median_error': 0,
            'std_error': 0,
            'min_error': 0,
            'max_error': 0,
            'p95_error': 0,
            'p99_error': 0,
            'delay_errors': [],
            'mean_delay': 0,
            'median_delay': 0,
            'std_delay': 0,
            'min_delay': 0,
            'max_delay': 0,
            'p95_delay': 0,
            'p99_delay': 0,
            'delays': []
        }
    
    # Convert emulator data to DataFrame
    emulator_df = pd.DataFrame(emulator_data)
    
    # Ensure column names are correct
    if 'timestamp' in emulator_df.columns:
        emulator_df = emulator_df.rename(columns={'timestamp': 'emulator_timestamp'})
    if 'time_stamp' in received_data.columns:
        received_data = received_data.rename(columns={'time_stamp': 'received_timestamp'})
    
    # Check if the necessary columns exist
    required_cols_emulator = ['emulator_timestamp', 'sequence', 'delay']
    required_cols_received = ['received_timestamp', 'sequence_number']
    
    for col in required_cols_emulator:
        if col not in emulator_df.columns:
            print(f"Warning: Required column '{col}' not found in emulator data")
            print(f"Available columns: {emulator_df.columns.tolist()}")
            return {
                'mean_error': 0,
                'median_error': 0,
                'std_error': 0,
                'min_error': 0,
                'max_error': 0,
                'p95_error': 0,
                'p99_error': 0,
                'delay_errors': [],
                'mean_delay': 0,
                'median_delay': 0,
                'std_delay': 0,
                'min_delay': 0,
                'max_delay': 0,
                'p95_delay': 0,
                'p99_delay': 0,
                'delays': []
            }
    
    for col in required_cols_received:
        if col not in received_data.columns:
            print(f"Warning: Required column '{col}' not found in received data")
            print(f"Available columns: {received_data.columns.tolist()}")
            return {
                'mean_error': 0,
                'median_error': 0,
                'std_error': 0,
                'min_error': 0,
                'max_error': 0,
                'p95_error': 0,
                'p99_error': 0,
                'delay_errors': [],
                'mean_delay': 0,
                'median_delay': 0,
                'std_delay': 0,
                'min_delay': 0,
                'max_delay': 0,
                'p95_delay': 0,
                'p99_delay': 0,
                'delays': []
            }
    
    # Convert timestamp from emulator (nanoseconds) to seconds to match received data
    emulator_df['emulator_timestamp'] = emulator_df['emulator_timestamp'] / 1e9
    
    # Convert delay from milliseconds to seconds
    if 'delay' in emulator_df.columns:
        emulator_df['delay'] = emulator_df['delay'] / 1000.0
        
    # Print scale information for debugging
    print(f"Emulator timestamp range: {emulator_df['emulator_timestamp'].min()} to {emulator_df['emulator_timestamp'].max()}")
    print(f"Received timestamp range: {received_data['received_timestamp'].min()} to {received_data['received_timestamp'].max()}")
    print(f"Delay range (seconds): {emulator_df['delay'].min()} to {emulator_df['delay'].max()}")
    
    # Merge data based on sequence number
    merged_data = pd.merge(
        emulator_df,
        received_data,
        left_on='sequence',
        right_on='sequence_number',
        how='inner'
    )
    
    if merged_data.empty:
        print("Warning: No matching packets found between emulator and received data")
        return {
            'mean_error': 0,
            'median_error': 0,
            'std_error': 0,
            'min_error': 0,
            'max_error': 0,
            'p95_error': 0,
            'p99_error': 0,
            'delay_errors': [],
            'mean_delay': 0,
            'median_delay': 0,
            'std_delay': 0,
            'min_delay': 0,
            'max_delay': 0,
            'p95_delay': 0,
            'p99_delay': 0,
            'delays': []
        }
    
    # Calculate delay error (emulator timestamp + delay - received timestamp)
    # All values should now be in seconds
    delay_errors = merged_data['emulator_timestamp'] + merged_data['delay'] - merged_data['received_timestamp']
    
    # Convert to absolute value for error calculations
    delay_errors_abs = np.abs(delay_errors)
    
    # Convert delay_errors to milliseconds for reporting
    delay_errors_ms = delay_errors * 1000.0
    delay_errors_abs_ms = delay_errors_abs * 1000.0
    
    # Get delays in milliseconds for reporting
    delays_ms = merged_data['delay'] * 1000.0
    
    # Calculate delay statistics (using absolute values for errors)
    delay_stats = {
        'mean_error': np.mean(delay_errors_abs_ms),
        'median_error': np.median(delay_errors_abs_ms),
        'std_error': np.std(delay_errors_abs_ms),
        'min_error': np.min(delay_errors_abs_ms),
        'max_error': np.max(delay_errors_abs_ms),
        'p95_error': np.percentile(delay_errors_abs_ms, 95),
        'p99_error': np.percentile(delay_errors_abs_ms, 99),
        'delay_errors': delay_errors_ms.tolist(),  # Keep signed values for plotting
        'delay_errors_abs': delay_errors_abs_ms.tolist(),  # Absolute values
        'mean_delay': np.mean(delays_ms),
        'median_delay': np.median(delays_ms),
        'std_delay': np.std(delays_ms),
        'min_delay': np.min(delays_ms),
        'max_delay': np.max(delays_ms),
        'p95_delay': np.percentile(delays_ms, 95),
        'p99_delay': np.percentile(delays_ms, 99),
        'delays': delays_ms.tolist()
    }
    
    return delay_stats

def plot_analysis(results: Dict, output_dir: str, condition: str, scenario: str):
    """
    Create plots of the analysis results.
    
    Args:
        results: Dictionary containing analysis results
        output_dir: Directory to save plots
        condition: Network condition (packet_loss, communication_loss, delay)
        scenario: Scenario name
    """
    if not results:
        print(f"Warning: No results to plot for {condition}/{scenario}")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    if condition in ['packet_loss', 'communication_loss']:
        # Create figure with two subplots for loss analysis
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Plot 1: Loss pattern
        ax1.set_title(f'Packet Loss Pattern - {condition} - {scenario}')
        ax1.set_xlabel('Packet Number')
        ax1.set_ylabel('Lost')
        
        # Create a binary array for lost packets
        lost_mask = np.zeros(results['total_packets'], dtype=bool)
        lost_mask[:results['lost_packets']] = True
        
        # Plot as a thin line
        ax1.plot(range(results['total_packets']), lost_mask, 'r-', linewidth=0.5)
        ax1.set_ylim(-0.1, 1.1)
        ax1.set_yticks([0, 1])
        ax1.set_yticklabels(['Received', 'Lost'])
        
        # Plot 2: Burst length distribution
        ax2.set_title('Burst Length Distribution')
        ax2.set_xlabel('Burst Length')
        ax2.set_ylabel('Count')
        
        if results['burst_stats']['burst_lengths']:
            ax2.hist(results['burst_stats']['burst_lengths'], bins=50, alpha=0.7)
            ax2.axvline(results['burst_stats']['mean'], color='r', linestyle='--', 
                       label=f'Mean: {results["burst_stats"]["mean"]:.2f}')
            ax2.axvline(results['burst_stats']['median'], color='g', linestyle='--',
                       label=f'Median: {results["burst_stats"]["median"]:.2f}')
            ax2.legend()
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'{condition}_{scenario}_loss_analysis.png'))
        plt.close()
        
    elif condition == 'delay':
        if 'delays' not in results or not results['delays']:
            print(f"Warning: No delay data available for {condition}/{scenario}")
            return
            
        # Create figure with three subplots for delay analysis
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 15))
        
        # Plot 1: Delay error distribution (absolute values)
        ax1.set_title(f'Delay Error Distribution (Absolute) - {scenario}')
        ax1.set_xlabel('Error (ms)')
        ax1.set_ylabel('Count')
        
        # Use absolute error values for the histogram
        if 'delay_errors_abs' in results:
            ax1.hist(results['delay_errors_abs'], bins=50, alpha=0.7)
        else:
            # Fall back to absolute values of delay_errors if delay_errors_abs not available
            ax1.hist(np.abs(results['delay_errors']), bins=50, alpha=0.7)
            
        ax1.axvline(results['mean_error'], color='r', linestyle='--',
                    label=f'Mean: {results["mean_error"]:.2f}ms')
        ax1.axvline(results['median_error'], color='g', linestyle='--',
                    label=f'Median: {results["median_error"]:.2f}ms')
        ax1.legend()
        
        # Plot 2: Delay distribution
        ax2.set_title('Applied Delay Distribution')
        ax2.set_xlabel('Delay (ms)')
        ax2.set_ylabel('Count')
        ax2.hist(results['delays'], bins=50, alpha=0.7)
        ax2.axvline(results['mean_delay'], color='r', linestyle='--',
                    label=f'Mean: {results["mean_delay"]:.2f}ms')
        ax2.axvline(results['median_delay'], color='g', linestyle='--',
                    label=f'Median: {results["median_delay"]:.2f}ms')
        ax2.legend()
        
        # Plot 3: Delay error vs Applied delay
        ax3.set_title('Delay Error vs Applied Delay')
        ax3.set_xlabel('Applied Delay (ms)')
        ax3.set_ylabel('Error (ms)')
        ax3.scatter(results['delays'], results['delay_errors'], alpha=0.5, s=1)
        ax3.axhline(y=0, color='r', linestyle='--')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'{condition}_{scenario}_delay_analysis.png'))
        plt.close()

def save_results_to_excel(results: Dict, output_dir: str, condition: str, scenario: str):
    """
    Save analysis results to an Excel file.
    
    Args:
        results: Dictionary containing analysis results
        output_dir: Directory to save Excel file
        condition: Network condition
        scenario: Scenario name
    """
    if not results:
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f'{condition}_{scenario}_analysis.xlsx')
    
    with pd.ExcelWriter(output_file) as writer:
        if condition in ['packet_loss', 'communication_loss']:
            # Overall statistics
            overall_stats = pd.DataFrame([{
                'Condition': condition,
                'Scenario': scenario,
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
            overall_stats.to_excel(writer, sheet_name='Overall Statistics', index=False)
            
            # Burst lengths
            burst_lengths = pd.DataFrame({
                'Burst Length': results['burst_stats']['burst_lengths']
            })
            burst_lengths.to_excel(writer, sheet_name='Burst Lengths', index=False)
            
        elif condition == 'delay':
            # Delay statistics (using absolute values for errors)
            delay_stats = pd.DataFrame([{
                'Condition': condition,
                'Scenario': scenario,
                'Mean Error (Absolute, ms)': results['mean_error'],
                'Median Error (Absolute, ms)': results['median_error'],
                'Std Error (Absolute, ms)': results['std_error'],
                'Min Error (Absolute, ms)': results['min_error'],
                'Max Error (Absolute, ms)': results['max_error'],
                'P95 Error (Absolute, ms)': results['p95_error'],
                'P99 Error (Absolute, ms)': results['p99_error'],
                'Mean Delay (ms)': results['mean_delay'],
                'Median Delay (ms)': results['median_delay'],
                'Std Delay (ms)': results['std_delay'],
                'Min Delay (ms)': results['min_delay'],
                'Max Delay (ms)': results['max_delay'],
                'P95 Delay (ms)': results['p95_delay'],
                'P99 Delay (ms)': results['p99_delay']
            }])
            delay_stats.to_excel(writer, sheet_name='Delay Statistics', index=False)
            
            # Create a DataFrame with both original and absolute error values
            if 'delay_errors_abs' in results:
                errors_df = pd.DataFrame({
                    'Error (ms)': results['delay_errors'],
                    'Absolute Error (ms)': results['delay_errors_abs'],
                    'Delay (ms)': results['delays']
                })
            else:
                errors_df = pd.DataFrame({
                    'Error (ms)': results['delay_errors'],
                    'Absolute Error (ms)': np.abs(results['delay_errors']),
                    'Delay (ms)': results['delays']
                })
            
            errors_df.to_excel(writer, sheet_name='Delay Errors', index=False)

def save_packet_data_to_csv2(packet_data_list: List[Dict], output_file: str):
    """
    Save packet data to a CSV file.
    
    Args:
        packet_data_list: List of dictionaries containing packet data
        output_file: Path to save the CSV file
    """
    if not packet_data_list:
        return
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["time_stamp", "sequence_number", "pos0_x", "pos0_y", "pos0_z", "rot0_x", "rot0_y", "rot0_z", 
                         "pos1_x", "pos1_y", "pos1_z", "rot1_x", "rot1_y", "rot1_z", "grasper0", "grasper1", "pedal", "drop"])
        for p in packet_data_list:
            pos0, rot0, grasp0 = get_psm_vars(p, 0)
            pos1, rot1, grasp1 = get_psm_vars(p, 1)
            ts, seq_num, pedal, drop = get_time_sequence_pedal_value(p)
            writer.writerow([ts, seq_num, *pos0, *rot0, *pos1, *rot1, grasp0, grasp1, pedal, drop])

    print(f"\nPacket data saved to {output_file}")

def save_packet_data_to_csv(packet_data_list: List[Dict], output_file: str):
    """
    Save packet data to a CSV file.
    
    Args:
        packet_data_list: List of dictionaries containing packet data
        output_file: Path to save the CSV file
    """
    if not packet_data_list:
        return
    
    # Convert to DataFrame and save to CSV
    df = pd.DataFrame(packet_data_list)
    df.to_csv(output_file, index=False)
    print(f"\nPacket data saved to {output_file}")


def analyze_experiment_data(experiment_dir: str, output_dir: str):
    """
    Analyze all experiment data in the given directory.
    
    Args:
        experiment_dir: Path to the experiment directory
        output_dir: Path to save analysis results
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each condition including no_fault
    conditions = ['packet_loss', 'communication_loss', 'delay']
    
    for condition in conditions:
        condition_dir = os.path.join(experiment_dir, condition)
        if not os.path.exists(condition_dir):
            print(f"Directory not found: {condition_dir}")
            continue
        
        # Process each scenario
        for scenario in os.listdir(condition_dir):
            scenario_dir = os.path.join(condition_dir, scenario)
            if not os.path.isdir(scenario_dir):
                continue
            
            print(f"\nProcessing {condition}/{scenario}...")
            
            # Read emulator data
            emulator_log = os.path.join(scenario_dir, 'console_data_complete_1.bin')
            if not os.path.exists(emulator_log):
                print(f"Emulator log not found: {emulator_log}")
                continue
                
            sequence_numbers, loss_flags, packet_data = read_packet_log(
                emulator_log, 
                is_delay=(condition == 'delay')
            )
            
            # Save extracted packet data to CSV in the scenario folder
            csv_output = os.path.join(scenario_dir, 'console_data_completed_1.csv')
            save_packet_data_to_csv2(packet_data, csv_output)
            
            if condition in ['packet_loss', 'communication_loss']:
                # Analyze packet loss
                results = analyze_packet_loss(sequence_numbers, loss_flags)
                
                # Create plots
                plot_analysis(results, output_dir, condition, scenario)
                
                # Save results
                save_results_to_excel(results, output_dir, condition, scenario)
                
            elif condition == 'delay':
                # Read received data
                received_data_file = os.path.join(scenario_dir, 'console_data_recieved_1.csv')
                if not os.path.exists(received_data_file):
                    print(f"Received data file not found: {received_data_file}")
                    continue
                    
                received_data = pd.read_csv(received_data_file)
                
                # Analyze delay
                results = analyze_delay(packet_data, received_data)
                
                # Create plots
                plot_analysis(results, output_dir, condition, scenario)
                
                # Save results
                save_results_to_excel(results, output_dir, condition, scenario)
                

    # Get the absolute path to analyze_no_fault.py in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    analyze_no_fault_path = os.path.join(script_dir, "analyze_no_fault.py")
    
    # Execute the script with absolute paths
    os.system(f"python {analyze_no_fault_path} --scenario_dir {experiment_dir} --output_dir {output_dir}")

if __name__ == "__main__":
    # import argparse
    
    # parser = argparse.ArgumentParser(description='Analyze network statistics from experiment data.')
    # parser.add_argument('--experiment_dir', required=True, help='Path to the experiment directory')
    # parser.add_argument('--output_dir', required=True, help='Path to save analysis results')
    # args = parser.parse_args()
    
    # analyze_experiment_data(args.experiment_dir, args.output_dir)
    analyze_experiment_data("tests/dVTrainer/Data/exp_data_3_new", "tests/dVTrainer/Data/exp_data_new_out")
