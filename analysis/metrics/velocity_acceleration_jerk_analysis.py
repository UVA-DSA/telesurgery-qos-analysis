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
from constants import *

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
        console_data_scaled[:, console_pos_cols] *= CONSOLE_SIM_SCALE
        
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
    
    def analyze_transfer_mp(self, robot_data, console_data, mp_dict, analyser_mp, scenario, configuration, color):
        """
        Analyze Motion Primitives within a single peg transfer and compute metrics for each MP
        """
        if robot_data is None or console_data is None or len(robot_data) < 2:
            return
        
        # Define position columns for both arms
        robot_pos_cols_left = [2, 3, 4]   # pos0_x, pos0_y, pos0_z (left arm)
        robot_pos_cols_right = [8, 9, 10]  # pos1_x, pos1_y, pos1_z (right arm)
        
        console_pos_cols_left = [2, 3, 4]   # pos0_x, pos0_y, pos0_z (left arm)  
        console_pos_cols_right = [8, 9, 10]  # pos1_x, pos1_y, pos1_z (right arm)
        
        # Determine which arm to use based on color
        left = ['Magenta', 'Yellow', 'Cyan']
        right = ['Red', 'Green', 'Blue']
        
        if color in right:
            robot_pos_cols = robot_pos_cols_right
            console_pos_cols = console_pos_cols_right
        else:
            robot_pos_cols = robot_pos_cols_left
            console_pos_cols = console_pos_cols_left
        
        # Get MP intervals for robot and console spaces
        try:
            mp_intervals_robot = analyser_mp.get_MP_index_interval_robot(mp_dict, robot_data, color)
            mp_intervals_console = analyser_mp.get_MP_index_interval_completed(mp_dict, console_data, color)
            
            # Initialize MP metrics
            mp_metrics = {
                'Touch_Peg': {'robot': {'velocity': 0, 'acceleration': 0, 'jerk': 0},
                             'console': {'velocity': 0, 'acceleration': 0, 'jerk': 0}},
                'Grasp': {'robot': {'velocity': 0, 'acceleration': 0, 'jerk': 0},
                         'console': {'velocity': 0, 'acceleration': 0, 'jerk': 0}},
                'Untouch': {'robot': {'velocity': 0, 'acceleration': 0, 'jerk': 0},
                           'console': {'velocity': 0, 'acceleration': 0, 'jerk': 0}},
                'Touch_Goal': {'robot': {'velocity': 0, 'acceleration': 0, 'jerk': 0},
                              'console': {'velocity': 0, 'acceleration': 0, 'jerk': 0}},
                'Release': {'robot': {'velocity': 0, 'acceleration': 0, 'jerk': 0},
                           'console': {'velocity': 0, 'acceleration': 0, 'jerk': 0}}
            }
            
            # Process each motion primitive
            for j in range(len(mp_intervals_robot)):
                if j >= len(mp_dict[color]):
                    break
                    
                mp_type = mp_dict[color][j][0]
                mp_name = None
                
                # Map MP types to our categories
                if mp_type == 'Touch' and type(mp_dict[color][j][1]) != str:
                    mp_name = 'Touch_Peg'
                elif mp_type == 'Grasp':
                    mp_name = 'Grasp'
                elif mp_type == 'Untouch':
                    mp_name = 'Untouch'
                elif mp_type == 'Touch' and type(mp_dict[color][j][1]) == str:
                    mp_name = 'Touch_Goal'
                elif mp_type == 'Release':
                    mp_name = 'Release'
                
                if mp_name is None:
                    continue
                
                # Extract robot data for this MP
                robot_start, robot_end = mp_intervals_robot[j]
                robot_mp_data = robot_data[robot_start:robot_end+1]
                
                if len(robot_mp_data) > 1:
                    # Compute robot metrics for this MP
                    robot_velocity = self.compute_position_velocities(robot_mp_data, 0, robot_pos_cols)
                    if len(robot_velocity) > 0:
                        mp_metrics[mp_name]['robot']['velocity'] += np.mean(robot_velocity)
                        
                        if len(robot_velocity) > 1:
                            robot_acceleration = self.compute_acceleration(robot_velocity, robot_mp_data[:, 0])
                            if len(robot_acceleration) > 0:
                                mp_metrics[mp_name]['robot']['acceleration'] += np.mean(np.abs(robot_acceleration))
                                
                                if len(robot_acceleration) > 1:
                                    robot_jerk = self.compute_jerk(robot_acceleration, robot_mp_data[:, 0])
                                    if len(robot_jerk) > 0:
                                        mp_metrics[mp_name]['robot']['jerk'] += np.mean(np.abs(robot_jerk))
                
                # Extract console data for this MP
                if j < len(mp_intervals_console):
                    console_start, console_end = mp_intervals_console[j]
                    console_mp_data = console_data[console_start:console_end+1].copy()
                    console_mp_data[:, console_pos_cols] *= CONSOLE_SIM_SCALE
                    
                    if len(console_mp_data) > 1:
                        # Compute console metrics for this MP
                        console_velocity = self.compute_position_velocities(console_mp_data, 0, console_pos_cols)
                        if len(console_velocity) > 0:
                            mp_metrics[mp_name]['console']['velocity'] += np.mean(console_velocity)
                            
                            if len(console_velocity) > 1:
                                console_acceleration = self.compute_acceleration(console_velocity, console_mp_data[:, 0])
                                if len(console_acceleration) > 0:
                                    mp_metrics[mp_name]['console']['acceleration'] += np.mean(np.abs(console_acceleration))
                                    
                                    if len(console_acceleration) > 1:
                                        console_jerk = self.compute_jerk(console_acceleration, console_mp_data[:, 0])
                                        if len(console_jerk) > 0:
                                            mp_metrics[mp_name]['console']['jerk'] += np.mean(np.abs(console_jerk))
            
            # Store MP metrics in our data structure
            # Structure: metrics_data[scenario][configuration][color][mp_name][space][metric] = value
            for mp_name in mp_metrics:
                if mp_name not in self.metrics_data[scenario][configuration][color]:
                    self.metrics_data[scenario][configuration][color][mp_name] = defaultdict(dict)
                
                for space in ['robot', 'console']:
                    for metric in ['velocity', 'acceleration', 'jerk']:
                        if mp_metrics[mp_name][space][metric] > 0:
                            self.metrics_data[scenario][configuration][color][mp_name][space][metric] = mp_metrics[mp_name][space][metric]
                            
        except Exception as e:
            print(f"  Warning: Could not analyze MPs for {color} transfer: {e}")

    def analyze_configuration_mp(self, scenario, configuration):
        """
        Analyze all transfers within a single configuration with MP breakdown
        """
        trial_path = os.path.join(self.exp_data_path, scenario, configuration)
        
        if not os.path.exists(trial_path):
            print(f"Warning: {trial_path} not found")
            return
            
        try:
            print(f"Analyzing {scenario}/{configuration} with MP breakdown...")
            
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
                        
                        # Analyze this transfer with MP breakdown
                        self.analyze_transfer_mp(robot_aligned, completed_aligned, mp_dict, analyser_mp, scenario, configuration, color)
                        
                    except Exception as e:
                        print(f"  Warning: Could not analyze {color} transfer: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error analyzing {scenario}/{configuration}: {e}")

    def analyze_all_trials_mp(self):
        """
        Analyze all trials across all scenarios and configurations with MP breakdown
        """
        for scenario in self.scenarios:
            print(f"\nProcessing scenario: {scenario}")
            for configuration in self.configuration_mappings[scenario]:
                self.analyze_configuration_mp(scenario, configuration)

    def get_mp_metrics_for_plotting(self, scenario, space, metric):
        """
        Extract MP-based metric data for plotting in the same format as motion_length_analysis.py
        Returns arrays for each MP category across all configurations
        """
        mp_categories = ['Touch_Peg', 'Grasp', 'Untouch', 'Touch_Goal', 'Release']
        data_by_config = []
        
        for config in self.configuration_mappings[scenario]:
            config_mp_metrics = [0, 0, 0, 0, 0]  # Initialize for each MP category
            transfer_counts = [0, 0, 0, 0, 0]    # Count valid transfers for averaging
            
            for color in self.colors:
                if (config in self.metrics_data[scenario] and 
                    color in self.metrics_data[scenario][config]):
                    
                    for i, mp_category in enumerate(mp_categories):
                        if (mp_category in self.metrics_data[scenario][config][color] and
                            space in self.metrics_data[scenario][config][color][mp_category] and
                            metric in self.metrics_data[scenario][config][color][mp_category][space]):
                            
                            config_mp_metrics[i] += self.metrics_data[scenario][config][color][mp_category][space][metric]
                            transfer_counts[i] += 1
            
            # Average across transfers for each MP
            config_averages = []
            for i in range(5):
                if transfer_counts[i] > 0:
                    config_averages.append(config_mp_metrics[i] / transfer_counts[i])
                else:
                    config_averages.append(0)
            
            data_by_config.append(config_averages)
        
        return data_by_config

    def get_no_fault_baseline_mp(self, space, metric):
        """
        Get no_fault baseline data for MP analysis (averaged across all no_fault configurations)
        """
        mp_categories = ['Touch_Peg', 'Grasp', 'Untouch', 'Touch_Goal', 'Release'] 
        baseline_mp_metrics = [0, 0, 0, 0, 0]
        transfer_counts = [0, 0, 0, 0, 0]
        
        for config in self.configuration_mappings['no_fault']:
            for color in self.colors:
                if (config in self.metrics_data['no_fault'] and 
                    color in self.metrics_data['no_fault'][config]):
                    
                    for i, mp_category in enumerate(mp_categories):
                        if (mp_category in self.metrics_data['no_fault'][config][color] and
                            space in self.metrics_data['no_fault'][config][color][mp_category] and
                            metric in self.metrics_data['no_fault'][config][color][mp_category][space]):
                            
                            baseline_mp_metrics[i] += self.metrics_data['no_fault'][config][color][mp_category][space][metric]
                            transfer_counts[i] += 1
        
        # Average across all no_fault transfers
        baseline_averages = []
        for i in range(5):
            if transfer_counts[i] > 0:
                baseline_averages.append(baseline_mp_metrics[i] / transfer_counts[i])
            else:
                baseline_averages.append(0)
        
        return baseline_averages

    def create_detailed_plots(self):
        """
        Create stacked bar plots with Motion Primitive breakdown similar to motion_length_analysis.py
        """
        import matplotlib.patches as mpatches
        from matplotlib.legend_handler import HandlerTuple
        from matplotlib.lines import Line2D
        
        metrics = ['velocity', 'acceleration', 'jerk']
        fault_scenarios = ['communication_loss', 'delay', 'packet_loss']
        
        # Define MP categories and colors matching motion_length_analysis.py
        mp_categories = ['Touch_Peg', 'Grasp', 'Untouch', 'Touch_Goal', 'Release']
        mp_labels = ['Touch Peg', 'Grasp', 'Untouch Start Pole', 'Touch Goal Pole', 'Release']
        colors = ["#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02C", "#FB9A99"]
        
        for metric in metrics:
            print(f"Creating MP-based plot for {metric}...")
            
            # Initialize data collection
            net_conditions = ['normal']
            mp_data_console = []
            mp_data_robot = []
            
            # Get no_fault baseline 
            baseline_console = self.get_no_fault_baseline_mp('console', metric)
            baseline_robot = self.get_no_fault_baseline_mp('robot', metric)
            mp_data_console.append(baseline_console)
            mp_data_robot.append(baseline_robot)
            
            # Collect fault scenario data
            for scenario in fault_scenarios:
                console_data = self.get_mp_metrics_for_plotting(scenario, 'console', metric)
                robot_data = self.get_mp_metrics_for_plotting(scenario, 'robot', metric)
                
                for i, config in enumerate(self.configuration_mappings[scenario]):
                    net_conditions.append(config)
                    if i < len(console_data):
                        mp_data_console.append(console_data[i])
                    else:
                        mp_data_console.append([0, 0, 0, 0, 0])
                    
                    if i < len(robot_data):
                        mp_data_robot.append(robot_data[i])
                    else:
                        mp_data_robot.append([0, 0, 0, 0, 0])
            
            # Convert to numpy arrays for plotting
            data_console = np.array(mp_data_console)
            data_robot = np.array(mp_data_robot)
            
            # Create the plot
            plt.figure(figsize=(18, 7), constrained_layout=True)
            
            x = np.arange(len(net_conditions))
            bar_width = 0.3
            x1 = x - bar_width / 2  # Robot bars (left)
            x2 = x + bar_width / 2  # Console bars (right)
            bottom1 = np.zeros(len(net_conditions))
            bottom2 = np.zeros(len(net_conditions))
            
            # Create stacked bars for each MP category
            for i in range(len(mp_categories)):
                # Left bar stack (robot)
                plt.bar(x1, data_robot[:, i], bottom=bottom1, color=colors[i], width=bar_width, alpha=0.5)
                for j in range(len(net_conditions)):
                    if data_robot[j, i] > 0:
                        plt.text(x1[j], bottom1[j] + data_robot[j, i]/2, f"{data_robot[j, i]:.3f}", 
                                ha='center', va='center', fontsize=7)
                bottom1 += data_robot[:, i]

                # Right bar stack (console)
                plt.bar(x2, data_console[:, i], bottom=bottom2, color=colors[i], width=bar_width, 
                        edgecolor='black', linewidth=1.2)
                for j in range(len(net_conditions)):
                    if data_console[j, i] > 0:
                        plt.text(x2[j], bottom2[j] + data_console[j, i]/2, f"{data_console[j, i]:.3f}", 
                                ha='center', va='center', fontsize=7)
                bottom2 += data_console[:, i]
            
            # Create legend handles
            legend_handles = []
            for i in range(len(mp_labels)):
                robot_patch = mpatches.Patch(color=colors[i], alpha=0.5)
                console_patch = mpatches.Patch(facecolor=colors[i], edgecolor='black', linewidth=1.2)
                legend_handles.append(((robot_patch, console_patch), mp_labels[i]))

            robot_type = mpatches.Patch(facecolor='gray', alpha=0.5)
            console_type = mpatches.Patch(facecolor='gray', edgecolor='black', linewidth=1.2)
            mean_console_line = Line2D([0], [0], color='red', linestyle='--')
            mean_robot_line = Line2D([0], [0], color='orange', linestyle='--')
            
            # Add vertical separators between scenario groups
            for idx in [3.5, 6.5]:  # After normal + 3 configs, after 3 delay configs
                if idx < len(net_conditions):
                    plt.axvline(x=idx - 0.5, color='gray', linestyle='--', linewidth=1.5, alpha=0.7)
            
            # Add reference lines for baseline totals
            baseline_console_total = np.sum(baseline_console)
            baseline_robot_total = np.sum(baseline_robot)
            if baseline_console_total > 0:
                plt.axhline(y=baseline_console_total, color='red', linestyle='--')
            if baseline_robot_total > 0:
                plt.axhline(y=baseline_robot_total, color='orange', linestyle='--')
            
            # Configure plot
            plt.xticks(x, net_conditions, rotation=45, fontsize=10)
            plt.ylabel(f'{metric.title()} (m/s{"²" if metric == "acceleration" else "³" if metric == "jerk" else ""})', fontsize=13)
            plt.title(f'{metric.title()} by Motion Primitive Across Network Conditions', fontsize=14)
            plt.grid(True, axis='y', linestyle='--', alpha=0.5)
            
            # Add comprehensive legend
            plt.legend(handles=[mean_console_line, mean_robot_line, robot_type, console_type] + 
                              [pair[0] for pair in legend_handles],
                      labels=['Console Mean of Normal Condition', 'Robot Mean of Normal Condition', 
                             'Robot Space (Left Bar)', 'Console Space (Right Bar)'] + 
                             [pair[1] for pair in legend_handles],
                      handler_map={tuple: HandlerTuple(ndivide=None)},
                      bbox_to_anchor=(1, 1.02), loc='upper left')
            
            plt.tight_layout(pad=2.0)
            plt.savefig(f'{metric}_mp_comparison_analysis.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"Saved {metric}_mp_comparison_analysis.png")
    
    def print_summary_statistics(self):
        """
        Print summary statistics for MP-based analysis
        """
        print("\n" + "="*80)
        print("MOTION PRIMITIVE-BASED ANALYSIS SUMMARY")
        print("="*80)
        
        mp_categories = ['Touch_Peg', 'Grasp', 'Untouch', 'Touch_Goal', 'Release']
        
        for scenario in self.scenarios:
            print(f"\n{scenario.upper().replace('_', ' ')}:")
            print("-" * 50)
            
            for config in self.configuration_mappings[scenario]:
                if config in self.metrics_data[scenario]:
                    print(f"\n  {config}:")
                    
                    for color in self.colors:
                        if color in self.metrics_data[scenario][config]:
                            print(f"    {color} transfer:")
                            
                            for mp_category in mp_categories:
                                if mp_category in self.metrics_data[scenario][config][color]:
                                    print(f"      {mp_category}:")
                                    
                                    for space in ['robot', 'console']:
                                        if space in self.metrics_data[scenario][config][color][mp_category]:
                                            print(f"        {space} space:")
                                            for metric, value in self.metrics_data[scenario][config][color][mp_category][space].items():
                                                print(f"          {metric}: {value:.6f}")
        
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

    def get_mp_data_with_std(self, scenario, space, metric):
        """
        Get MP data with means and standard deviations for scatter plots
        Returns dict with config names as keys, values are tuples of (means, stds) for each MP
        """
        mp_categories = ['Touch_Peg', 'Grasp', 'Untouch', 'Touch_Goal', 'Release']
        config_data = {}
        
        for config in self.configuration_mappings[scenario]:
            # Collect all values for each MP across all transfers
            mp_values = [[] for _ in range(5)]  # 5 MP categories
            
            for color in self.colors:
                if (config in self.metrics_data[scenario] and 
                    color in self.metrics_data[scenario][config]):
                    
                    for i, mp_category in enumerate(mp_categories):
                        if (mp_category in self.metrics_data[scenario][config][color] and
                            space in self.metrics_data[scenario][config][color][mp_category] and
                            metric in self.metrics_data[scenario][config][color][mp_category][space]):
                            
                            mp_values[i].append(self.metrics_data[scenario][config][color][mp_category][space][metric])
            
            # Calculate means and stds
            means = []
            stds = []
            for i in range(5):
                if len(mp_values[i]) > 0:
                    means.append(np.mean(mp_values[i]))
                    stds.append(np.std(mp_values[i]) if len(mp_values[i]) > 1 else 0)
                else:
                    means.append(0)
                    stds.append(0)
            
            config_data[config] = (means, stds)
        
        return config_data

    def get_no_fault_mp_data_with_std(self, space, metric):
        """
        Get aggregated no_fault MP data with means and standard deviations
        """
        mp_categories = ['Touch_Peg', 'Grasp', 'Untouch', 'Touch_Goal', 'Release']
        
        # Collect all values for each MP across all no_fault configurations and transfers
        mp_values = [[] for _ in range(5)]  # 5 MP categories
        
        for config in self.configuration_mappings['no_fault']:
            for color in self.colors:
                if (config in self.metrics_data['no_fault'] and 
                    color in self.metrics_data['no_fault'][config]):
                    
                    for i, mp_category in enumerate(mp_categories):
                        if (mp_category in self.metrics_data['no_fault'][config][color] and
                            space in self.metrics_data['no_fault'][config][color][mp_category] and
                            metric in self.metrics_data['no_fault'][config][color][mp_category][space]):
                            
                            mp_values[i].append(self.metrics_data['no_fault'][config][color][mp_category][space][metric])
        
        # Calculate means and stds
        means = []
        stds = []
        for i in range(5):
            if len(mp_values[i]) > 0:
                means.append(np.mean(mp_values[i]))
                stds.append(np.std(mp_values[i]) if len(mp_values[i]) > 1 else 0)
            else:
                means.append(0)
                stds.append(0)
        
        return means, stds

    def create_scatter_line_plots(self):
        """
        Create scatter line plots showing metric values across Motion Primitives for different configurations
        """
        metrics = ['velocity', 'acceleration', 'jerk']
        
        # MP categories in execution order
        mp_categories = ['Touch_Peg', 'Grasp', 'Untouch', 'Touch_Goal', 'Release']
        mp_labels = ['Touch Peg', 'Grasp', 'Untouch Start Pole', 'Touch Goal Pole', 'Release']
        
        # Only show specific configurations
        selected_configs = ['normal', 'communicationloss3', 'delay3', 'packetloss3']
        
        # Define colors and markers for selected configurations
        config_styles = {
            'normal': {'color': '#2E8B57', 'marker': 'o', 'label': 'No Fault'},  # Sea Green, circle
            'communicationloss3': {'color': '#DC143C', 'marker': 's', 'label': 'Comm Loss 3'},  # Crimson, square
            'delay3': {'color': '#191970', 'marker': '^', 'label': 'Delay 3'},  # Midnight Blue, triangle
            'packetloss3': {'color': '#FF8C00', 'marker': 'D', 'label': 'Packet Loss 3'}  # Dark Orange, diamond
        }
        
        for metric in metrics:
            print(f"Creating scatter line plot for {metric}...")
            
            plt.figure(figsize=(12, 8))
            
            config_data = {}
            
            # Get no_fault baseline data
            no_fault_robot_means, no_fault_robot_stds = self.get_no_fault_mp_data_with_std('robot', metric)
            no_fault_console_means, no_fault_console_stds = self.get_no_fault_mp_data_with_std('console', metric)
            
            config_data['normal'] = {
                'robot': (no_fault_robot_means, no_fault_robot_stds),
                'console': (no_fault_console_means, no_fault_console_stds)
            }
            
            # Collect specific fault configurations
            fault_scenarios = ['communication_loss', 'delay', 'packet_loss']
            target_configs = ['communicationloss3', 'delay3', 'packetloss3']
            
            for scenario in fault_scenarios:
                robot_data = self.get_mp_data_with_std(scenario, 'robot', metric)
                console_data = self.get_mp_data_with_std(scenario, 'console', metric)
                
                for config in target_configs:
                    if config in robot_data:
                        config_data[config] = {
                            'robot': robot_data[config],
                            'console': console_data.get(config, ([0, 0, 0, 0, 0], [0, 0, 0, 0, 0]))
                        }
            
            x_positions = np.arange(len(mp_labels))
            
            # Plot each selected configuration
            for config in selected_configs:
                if config not in config_data:
                    continue
                    
                style = config_styles[config]
                color = style['color']
                marker = style['marker']
                label = style['label']
                
                # Robot space (lower opacity, dashed lines, hollow markers)
                robot_means, robot_stds = config_data[config]['robot']
                if any(m > 0 for m in robot_means):  # Only plot if there's data
                    plt.errorbar(x_positions, robot_means, yerr=robot_stds, 
                                color=color, marker=marker, linestyle='--', alpha=0.6,
                                linewidth=2, markersize=6, capsize=4,
                                markerfacecolor='none', markeredgewidth=2)
                
                # Console space (solid lines, high opacity, filled markers)  
                console_means, console_stds = config_data[config]['console']
                if any(m > 0 for m in console_means):  # Only plot if there's data
                    plt.errorbar(x_positions, console_means, yerr=console_stds,
                                color=color, marker=marker, linestyle='-', alpha=0.9,
                                linewidth=2, markersize=8, capsize=4,
                                markerfacecolor=color, markeredgewidth=1, label=label)
            
            # Add style explanation to legend
            from matplotlib.lines import Line2D
            legend_elements = []
            
            # Add configuration entries
            for config in selected_configs:
                if config in config_data:
                    style = config_styles[config]
                    legend_elements.append(Line2D([0], [0], marker=style['marker'], color=style['color'],
                                                 linewidth=2, markersize=8, label=style['label']))
            
            # Add style explanation
            legend_elements.append(Line2D([0], [0], color='gray', linestyle='-', alpha=0.9, 
                                         marker='o', markerfacecolor='gray', label='Console Space'))
            legend_elements.append(Line2D([0], [0], color='gray', linestyle='--', alpha=0.6,
                                         marker='o', markerfacecolor='none', markeredgewidth=2, label='Robot Space'))
            
            # Customize plot
            plt.xticks(x_positions, mp_labels, rotation=15, ha='right')
            plt.xlabel('Motion Primitives', fontsize=12)
            plt.ylabel(f'{metric.title()} (m/s{"²" if metric == "acceleration" else "³" if metric == "jerk" else ""})', fontsize=12)
            plt.title(f'{metric.title()} Across Motion Primitives by Configuration', fontsize=14)
            plt.grid(True, alpha=0.3)
            
            # Add simplified legend
            plt.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
            
            plt.tight_layout()
            plt.savefig(f'{metric}_mp_scatter_analysis.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"Saved {metric}_mp_scatter_analysis.png")


def main():
    """
    Main function to run the analysis
    """
    # Initialize analyzer
    analyzer = VelocityJerkAnalyzer("exp_data_new")
    
    print("Starting Motion Primitive-based Velocity, Acceleration, and Jerk Analysis...")
    print("Using AnalyserMP for motion primitive segmentation and coordinate transformation...")
    print("="*80)
    
    # Analyze all trials with MP breakdown
    analyzer.analyze_all_trials_mp()
    
    # Print summary statistics
    analyzer.print_summary_statistics()
    
    # Create detailed MP-based plots
    print("\nCreating detailed Motion Primitive-based analysis plots...")
    print("Generating stacked bar plots for each metric with MP breakdown...")
    analyzer.create_detailed_plots()
    
    # Create scatter line plots
    print("\nCreating scatter line plots for each metric...")
    analyzer.create_scatter_line_plots()
    
    print("\nAnalysis complete! Check the generated PNG files for results:")
    print("- velocity_mp_comparison_analysis.png")
    print("- acceleration_mp_comparison_analysis.png") 
    print("- jerk_mp_comparison_analysis.png")
    print("- velocity_mp_scatter_analysis.png")
    print("- acceleration_mp_scatter_analysis.png")
    print("- jerk_mp_scatter_analysis.png")


if __name__ == "__main__":
    main() 