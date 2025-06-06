import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# Add the metrics directory to path to import AnalyserMP
sys.path.append(os.path.join(os.path.dirname(__file__), 'metrics'))
from Analyser_mp import AnalyserMP

class VelocityJerkAnalyzer:
    def __init__(self, exp_data_path):
        """
        Initialize the analyzer with the path to experiment data
        """
        self.exp_data_path = exp_data_path
        self.scenarios = ['no_fault', 'communication_loss', 'delay', 'packet_loss']
        self.configuration_mappings = {
            'no_fault': ['freefault1', 'freefault2', 'freefault3'],
            'communication_loss': ['communicationloss1', 'communicationloss2', 'communicationloss3'],
            'delay': ['delay1', 'delay2', 'delay3'],
            'packet_loss': ['packetloss1', 'packetloss2', 'packetloss3']
        }
        
        # Colors representing different peg transfers
        self.colors = ['Red', 'Green', 'Blue', 'Magenta', 'Yellow', 'Cyan']
        
        # Data will store metrics for each transfer
        # Structure: metrics_data[scenario][configuration][color][space][metric] = value
        self.metrics_data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict))))
        
    def compute_position_velocities(self, data, dt_col=0, pos_cols=None):
        """
        Compute velocity from position data with proper timestamp handling
        """
        if data is None or len(data) < 2:
            return np.array([])
            
        timestamps = data[:, dt_col]
        dt = np.diff(timestamps)
        
        # Remove zero or negative time differences
        valid_indices = dt > 0
        if not np.any(valid_indices):
            return np.array([])
        
        dt = dt[valid_indices]
        
        velocities = []
        for pos_col in pos_cols:
            pos = data[:, pos_col]
            vel = np.diff(pos)[valid_indices] / dt
            velocities.append(vel)
        
        # Compute magnitude of velocity vector
        velocity_magnitudes = np.sqrt(sum(v**2 for v in velocities))
        
        return velocity_magnitudes
    
    def compute_acceleration(self, velocity, timestamps):
        """
        Compute acceleration from velocity data
        """
        if len(velocity) < 2:
            return np.array([])
            
        # Use timestamps corresponding to velocity data
        vel_timestamps = timestamps[1:len(velocity)+1] if len(timestamps) > len(velocity) else timestamps[1:]
        dt = np.diff(vel_timestamps)
        
        valid_indices = dt > 0
        if not np.any(valid_indices):
            return np.array([])
            
        dt = dt[valid_indices]
        acceleration = np.diff(velocity)[valid_indices] / dt
        
        return acceleration
    
    def compute_jerk(self, acceleration, timestamps):
        """
        Compute jerk from acceleration data
        """
        if len(acceleration) < 2:
            return np.array([])
            
        # Use timestamps corresponding to acceleration data
        acc_timestamps = timestamps[2:len(acceleration)+2] if len(timestamps) > len(acceleration)+1 else timestamps[2:]
        dt = np.diff(acc_timestamps)
        
        valid_indices = dt > 0
        if not np.any(valid_indices):
            return np.array([])
            
        dt = dt[valid_indices]
        jerk = np.diff(acceleration)[valid_indices] / dt
        
        return jerk
    
    def analyze_transfer(self, robot_data, console_data, scenario, configuration, color):
        """
        Analyze a single peg transfer and compute metrics
        """
        if robot_data is None or console_data is None or len(robot_data) < 2:
            return
        
        # Define position columns for both arms
        robot_pos_cols_left = [2, 3, 4]   # pos0_x, pos0_y, pos0_z (left arm)
        robot_pos_cols_right = [8, 9, 10]  # pos1_x, pos1_y, pos1_z (right arm)
        
        console_pos_cols_left = [2, 3, 4]   # pos0_x, pos0_y, pos0_z (left arm)  
        console_pos_cols_right = [8, 9, 10]  # pos1_x, pos1_y, pos1_z (right arm)
        
        # Determine which arm to use based on color
        # Right arm: Red, Green, Blue
        # Left arm: Magenta, Yellow, Cyan
        if color in ['Red', 'Green', 'Blue']:
            robot_pos_cols = robot_pos_cols_right
            console_pos_cols = console_pos_cols_right
        else:
            robot_pos_cols = robot_pos_cols_left
            console_pos_cols = console_pos_cols_left
        
        # Compute metrics for robot space
        robot_velocity = self.compute_position_velocities(robot_data, 0, robot_pos_cols)
        robot_acceleration = np.array([])
        robot_jerk = np.array([])
        
        if len(robot_velocity) > 1:
            robot_acceleration = self.compute_acceleration(robot_velocity, robot_data[:, 0])
            if len(robot_acceleration) > 1:
                robot_jerk = self.compute_jerk(robot_acceleration, robot_data[:, 0])
        
        # Store robot metrics
        if len(robot_velocity) > 0:
            self.metrics_data[scenario][configuration][color]['robot']['velocity'] = np.mean(robot_velocity)
        if len(robot_acceleration) > 0:
            self.metrics_data[scenario][configuration][color]['robot']['acceleration'] = np.mean(np.abs(robot_acceleration))
        if len(robot_jerk) > 0:
            self.metrics_data[scenario][configuration][color]['robot']['jerk'] = np.mean(np.abs(robot_jerk))
        
        # Compute metrics for console space (apply 0.15 scaling factor)
        # Scale console data by 0.15 since commands are scaled down before being applied to robot
        console_data_scaled = console_data.copy()
        console_data_scaled[:, console_pos_cols] *= 0.15
        
        console_velocity = self.compute_position_velocities(console_data_scaled, 0, console_pos_cols)
        console_acceleration = np.array([])
        console_jerk = np.array([])
        
        if len(console_velocity) > 1:
            console_acceleration = self.compute_acceleration(console_velocity, console_data_scaled[:, 0])
            if len(console_acceleration) > 1:
                console_jerk = self.compute_jerk(console_acceleration, console_data_scaled[:, 0])
        
        # Store console metrics
        if len(console_velocity) > 0:
            self.metrics_data[scenario][configuration][color]['console']['velocity'] = np.mean(console_velocity)
        if len(console_acceleration) > 0:
            self.metrics_data[scenario][configuration][color]['console']['acceleration'] = np.mean(np.abs(console_acceleration))
        if len(console_jerk) > 0:
            self.metrics_data[scenario][configuration][color]['console']['jerk'] = np.mean(np.abs(console_jerk))
    
    def analyze_configuration(self, scenario, configuration):
        """
        Analyze all transfers within a single configuration
        """
        trial_path = os.path.join(self.exp_data_path, scenario, configuration)
        
        if not os.path.exists(trial_path):
            print(f"Warning: {trial_path} not found")
            return
            
        try:
            print(f"Analyzing {scenario}/{configuration}...")
            
            # Use AnalyserMP to properly load and segment data
            analyser_mp = AnalyserMP(trial_path)
            
            # Get motion primitive dictionary with error information
            mp_dict = analyser_mp.get_MP_timestamp_error()
            
            # Process each color (peg transfer)
            for color in self.colors:
                if color in mp_dict and len(mp_dict[color]) > 0:
                    try:
                        # Get kinematic data for this specific transfer
                        robot_data, transformed_data, completed_data = analyser_mp.get_one_peg_kinematic_data_new(mp_dict, color)
                        
                        # Align console data to robot coordinate system
                        robot_aligned, transformed_aligned, completed_aligned = analyser_mp.align_console_kinematic_data_new(
                            robot_data, transformed_data, completed_data
                        )
                        
                        # Analyze this transfer
                        self.analyze_transfer(robot_aligned, completed_aligned, scenario, configuration, color)
                        
                    except Exception as e:
                        print(f"  Warning: Could not analyze {color} transfer: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error analyzing {scenario}/{configuration}: {e}")
    
    def analyze_all_trials(self):
        """
        Analyze all trials across all scenarios and configurations
        """
        for scenario in self.scenarios:
            print(f"\nProcessing scenario: {scenario}")
            for configuration in self.configuration_mappings[scenario]:
                self.analyze_configuration(scenario, configuration)
    
    def get_metric_data_for_plotting(self, scenario, space, metric):
        """
        Extract metric data for a specific scenario, space, and metric
        """
        data_by_config = {}
        
        for config in self.configuration_mappings[scenario]:
            config_data = []
            for color in self.colors:
                if (config in self.metrics_data[scenario] and 
                    color in self.metrics_data[scenario][config] and 
                    space in self.metrics_data[scenario][config][color] and
                    metric in self.metrics_data[scenario][config][color][space]):
                    
                    config_data.append(self.metrics_data[scenario][config][color][space][metric])
            
            data_by_config[config] = config_data
        
        return data_by_config
    
    def get_no_fault_baseline(self, space, metric):
        """
        Get no_fault baseline data (all transfers from all configurations combined)
        """
        baseline_data = []
        
        for config in self.configuration_mappings['no_fault']:
            for color in self.colors:
                if (config in self.metrics_data['no_fault'] and 
                    color in self.metrics_data['no_fault'][config] and 
                    space in self.metrics_data['no_fault'][config][color] and
                    metric in self.metrics_data['no_fault'][config][color][space]):
                    
                    baseline_data.append(self.metrics_data['no_fault'][config][color][space][metric])
        
        return baseline_data
    
    def create_detailed_plots(self):
        """
        Create detailed plots as specified: 9 figures total (3 scenarios × 3 metrics)
        Each figure has 6 subplots (3 configurations × 2 spaces)
        """
        metrics = ['velocity', 'acceleration', 'jerk']
        fault_scenarios = ['communication_loss', 'delay', 'packet_loss']
        spaces = ['console', 'robot']
        
        # Create 9 figures (3 scenarios × 3 metrics)
        for scenario in fault_scenarios:
            for metric in metrics:
                fig, axes = plt.subplots(3, 2, figsize=(16, 18))
                fig.suptitle(f'{scenario.replace("_", " ").title()} - {metric.title()} Analysis', fontsize=16)
                
                # Get no_fault baseline for this metric
                baseline_console = self.get_no_fault_baseline('console', metric)
                baseline_robot = self.get_no_fault_baseline('robot', metric)
                
                # Get data for this scenario and metric
                console_data = self.get_metric_data_for_plotting(scenario, 'console', metric)
                robot_data = self.get_metric_data_for_plotting(scenario, 'robot', metric)
                
                # Create subplots for each configuration
                for i, config in enumerate(self.configuration_mappings[scenario]):
                    
                    # Console space subplot (left column)
                    ax_console = axes[i, 0]
                    plot_data_console = []
                    plot_labels_console = []
                    colors_console = []
                    
                    if baseline_console:
                        plot_data_console.append(baseline_console)
                        plot_labels_console.append('No Fault\n(baseline)')
                        colors_console.append('lightblue')
                    
                    if config in console_data and console_data[config]:
                        plot_data_console.append(console_data[config])
                        clean_config = config.replace(scenario.split('_')[0], '').replace('loss', '')
                        if clean_config.startswith('_'):
                            clean_config = clean_config[1:]
                        plot_labels_console.append(f'{clean_config}\n({len(console_data[config])} transfers)')
                        colors_console.append('lightcoral')
                    
                    if plot_data_console:
                        bp_console = ax_console.boxplot(plot_data_console, labels=plot_labels_console, patch_artist=True)
                        for patch, color in zip(bp_console['boxes'], colors_console):
                            patch.set_facecolor(color)
                            patch.set_alpha(0.7)
                    
                    ax_console.set_title(f'Console Space - {config}')
                    ax_console.set_ylabel(f'{metric.title()} (m/s{"²" if metric == "acceleration" else "³" if metric == "jerk" else ""})')
                    ax_console.grid(True, alpha=0.3)
                    ax_console.tick_params(axis='x', labelsize=10)
                    
                    # Robot space subplot (right column)
                    ax_robot = axes[i, 1]
                    plot_data_robot = []
                    plot_labels_robot = []
                    colors_robot = []
                    
                    if baseline_robot:
                        plot_data_robot.append(baseline_robot)
                        plot_labels_robot.append('No Fault\n(baseline)')
                        colors_robot.append('lightblue')
                    
                    if config in robot_data and robot_data[config]:
                        plot_data_robot.append(robot_data[config])
                        clean_config = config.replace(scenario.split('_')[0], '').replace('loss', '')
                        if clean_config.startswith('_'):
                            clean_config = clean_config[1:]
                        plot_labels_robot.append(f'{clean_config}\n({len(robot_data[config])} transfers)')
                        colors_robot.append('lightcoral')
                    
                    if plot_data_robot:
                        bp_robot = ax_robot.boxplot(plot_data_robot, labels=plot_labels_robot, patch_artist=True)
                        for patch, color in zip(bp_robot['boxes'], colors_robot):
                            patch.set_facecolor(color)
                            patch.set_alpha(0.7)
                    
                    ax_robot.set_title(f'Robot Space - {config}')
                    ax_robot.set_ylabel(f'{metric.title()} (m/s{"²" if metric == "acceleration" else "³" if metric == "jerk" else ""})')
                    ax_robot.grid(True, alpha=0.3)
                    ax_robot.tick_params(axis='x', labelsize=10)
                    
                    # Add statistics text
                    if baseline_console and config in console_data and console_data[config]:
                        baseline_mean = np.mean(baseline_console)
                        config_mean = np.mean(console_data[config])
                        ax_console.text(0.02, 0.98, f'Baseline: {baseline_mean:.4f}\nConfig: {config_mean:.4f}', 
                                      transform=ax_console.transAxes, verticalalignment='top',
                                      bbox=dict(boxstyle='round', facecolor='white', alpha=0.8), fontsize=9)
                    
                    if baseline_robot and config in robot_data and robot_data[config]:
                        baseline_mean = np.mean(baseline_robot)
                        config_mean = np.mean(robot_data[config])
                        ax_robot.text(0.02, 0.98, f'Baseline: {baseline_mean:.4f}\nConfig: {config_mean:.4f}', 
                                    transform=ax_robot.transAxes, verticalalignment='top',
                                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8), fontsize=9)
                
                plt.tight_layout()
                plt.savefig(f'{scenario}_{metric}_transfer_analysis.png', dpi=300, bbox_inches='tight')
                # plt.show()  # Removed to only save figures to disk
    
    def print_summary_statistics(self):
        """
        Print summary statistics for all metrics
        """
        print("\n" + "="*80)
        print("TRANSFER-BASED ANALYSIS SUMMARY")
        print("="*80)
        
        for scenario in self.scenarios:
            print(f"\n{scenario.upper().replace('_', ' ')}:")
            print("-" * 50)
            
            for config in self.configuration_mappings[scenario]:
                if config in self.metrics_data[scenario]:
                    print(f"\n  {config}:")
                    
                    for color in self.colors:
                        if color in self.metrics_data[scenario][config]:
                            print(f"    {color} transfer:")
                            
                            for space in ['robot', 'console']:
                                if space in self.metrics_data[scenario][config][color]:
                                    print(f"      {space} space:")
                                    for metric, value in self.metrics_data[scenario][config][color][space].items():
                                        print(f"        {metric}: {value:.6f}")
        
        # Print transfer counts
        print(f"\n{'='*80}")
        print("TRANSFER COUNTS BY SCENARIO AND CONFIGURATION")
        print("="*80)
        
        for scenario in self.scenarios:
            print(f"\n{scenario.upper().replace('_', ' ')}:")
            for config in self.configuration_mappings[scenario]:
                if config in self.metrics_data[scenario]:
                    transfer_count = len([color for color in self.colors 
                                        if color in self.metrics_data[scenario][config]])
                    print(f"  {config}: {transfer_count} transfers")


def main():
    """
    Main function to run the analysis
    """
    # Initialize analyzer
    analyzer = VelocityJerkAnalyzer("exp_data_new")
    
    print("Starting Transfer-based Velocity, Acceleration, and Jerk Analysis...")
    print("Using AnalyserMP for motion primitive segmentation and coordinate transformation...")
    print("="*80)
    
    # Analyze all trials
    analyzer.analyze_all_trials()
    
    # Print summary statistics
    analyzer.print_summary_statistics()
    
    # Create detailed plots
    print("\nCreating detailed transfer-based analysis plots...")
    print("Generating 9 figures (3 scenarios × 3 metrics)...")
    analyzer.create_detailed_plots()
    
    print("\nAnalysis complete! Check the generated PNG files for results.")


if __name__ == "__main__":
    main() 