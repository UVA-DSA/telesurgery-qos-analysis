import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon
import seaborn as sns
from typing import List, Dict, Tuple
import re


class SurveyVisualizer:
    """Class to visualize System Usability Score and NASA TLX survey data."""
    
    def __init__(self, csv_path: str):
        """Initialize with CSV file path."""
        self.csv_path = csv_path
        self.df = None
        self.load_data()
    
    def load_data(self):
        """Load and preprocess the survey data."""
        # Read CSV, skipping the first row which contains metadata
        self.df = pd.read_csv(self.csv_path, skiprows=[2])  # Skip the JSON metadata row
        
        # Clean participant IDs and remove any test entries
        self.df = self.df[self.df['Participant ID'].notna()]
        self.df = self.df[~self.df['Participant ID'].str.contains('Test', na=False, case=False)]
        
        print(f"Loaded data for {len(self.df)} participants")
        print(f"Available participants: {list(self.df['Participant ID'].unique())}")
    
    def get_sus_questions(self) -> Dict[str, str]:
        """Extract SUS question labels from the header row."""
        # Read the header row to get question text
        header_df = pd.read_csv(self.csv_path, nrows=2)
        sus_questions = {}
        
        for i in range(1, 11):
            col_name = f'Q{i}'
            if col_name in header_df.columns:
                question_text = header_df[col_name].iloc[1]  # Second row contains questions
                # Truncate long questions for better display
                if len(question_text) > 50:
                    question_text = question_text[:47] + "..."
                sus_questions[col_name] = question_text
        
        return sus_questions
    
    def get_tlx_questions(self) -> Dict[str, str]:
        """Extract NASA TLX question labels from the header row."""
        # Read the header row to get question text
        header_df = pd.read_csv(self.csv_path, nrows=2)
        tlx_questions = {}
        
        # Pattern to match TLX columns (T1Q1, T2Q1, etc.)
        for col in header_df.columns:
            if re.match(r'T\d+Q\d+$', col):
                question_text = header_df[col].iloc[0]  # Second row contains questions
                # Extract the part before the first dash for axis labels
                if ' - ' in question_text:
                    label = question_text.split(' - ')[0]
                else:
                    label = question_text.split('.')[0] if '.' in question_text else question_text
                tlx_questions[col] = label.strip()
        
        return tlx_questions
    
    def parse_tlx_scenarios(self, participant_id: str) -> List[str]:
        """Parse TLX scenario labels for a participant."""
        participant_data = self.df[self.df['Participant ID'] == participant_id]
        print(participant_data)
        if len(participant_data) == 0:
            return []
        
        tlx_list = participant_data['TLXList'].iloc[0]
        if pd.isna(tlx_list):
            return [f"Scenario {i+1}" for i in range(4)]
        
        # Split by comma and clean up
        scenarios = [s.strip() for s in str(tlx_list).split(',')]
        if len(scenarios) != 4:
            scenarios.extend([f"Scenario {i+len(scenarios)+1}" for i in range(4-len(scenarios))])
        
        return scenarios[:4]
    
    def create_sus_boxplots(self, participant_ids: List[str]) -> plt.Figure:
        """Create box plots for SUS scores."""
        # Filter data for specified participants
        filtered_df = self.df[self.df['Participant ID'].isin(participant_ids)]
        
        if len(filtered_df) == 0:
            raise ValueError(f"No data found for participants: {participant_ids}")
        
        # Get SUS questions
        sus_questions = self.get_sus_questions()
        sus_columns = [f'Q{i}' for i in range(1, 11)]
        
        # Prepare data for plotting
        sus_data = []
        for _, row in filtered_df.iterrows():
            for col in sus_columns:
                if col in row and pd.notna(row[col]):
                    try:
                        # Handle different response formats
                        value = row[col]
                        if isinstance(value, str):
                            # Extract numeric value from strings like "5 - Strongly Agree"
                            if ' - ' in value:
                                value = value.split(' - ')[0]
                            value = float(value)
                        sus_data.append({
                            'Participant': row['Participant ID'],
                            'Question': col,
                            'Score': value
                        })
                    except (ValueError, TypeError):
                        continue
        
        sus_df = pd.DataFrame(sus_data)
        
        # Create box plot
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Create box plot
        box_plot = sns.boxplot(data=sus_df, x='Question', y='Score', ax=ax, 
                              palette='viridis', showfliers=True)
        
        # Overlay individual points
        sns.stripplot(data=sus_df, x='Question', y='Score', ax=ax, 
                     color='red', alpha=0.7, size=6)
        
        # Customize the plot
        ax.set_title(f'System Usability Score (SUS)', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('SUS Questions', fontsize=12, fontweight='bold')
        ax.set_ylabel('Score (1-5)', fontsize=12, fontweight='bold')
        ax.set_ylim(0.5, 5.5)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Add grid for better readability
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add question labels as tooltips (simplified version)
        question_labels = [sus_questions.get(f'Q{i}', f'Q{i}') for i in range(1, 11)]
        
        plt.tight_layout()
        return fig
    
    def create_radar_plot(self, participant_ids: List[str]) -> plt.Figure:
        """Create averaged radar plot for NASA TLX scores across participants."""
        # Filter data for specified participants
        filtered_df = self.df[self.df['Participant ID'].isin(participant_ids)]
        
        if len(filtered_df) == 0:
            raise ValueError(f"No data found for participants: {participant_ids}")
        
        # Get TLX questions and unique question types
        tlx_questions = self.get_tlx_questions()
        
        # Extract unique question types (should be 6: Mental, Physical, Temporal, Performance, Effort, Frustration)
        question_types = []
        for col, label in tlx_questions.items():
            if re.match(r'T1Q\d+$', col):  # Only look at T1 questions to get the 6 types
                question_types.append(label)
        
        if len(question_types) == 0:
            raise ValueError("No TLX questions found")
        
        num_vars = len(question_types)
        
        # Create single figure
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        # Calculate angles for each axis
        angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
        angles += angles[:1]  # Complete the circle
        
        # Color palette for scenarios
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
        
        # Get all unique scenarios across all participants
        all_scenarios = set()
        participant_scenario_maps = {}
        
        for _, row in filtered_df.iterrows():
            participant_id = row['Participant ID']
            participant_scenarios = self.parse_tlx_scenarios(participant_id)
            participant_scenario_maps[participant_id] = participant_scenarios
            all_scenarios.update(participant_scenarios)
        
        scenarios = list(all_scenarios)
        print(f"All scenarios found: {scenarios}")
        print(f"Participant scenario mappings: {participant_scenario_maps}")
        
        # Calculate average values for each unique scenario across all participants
        for scenario_idx, scenario_name in enumerate(scenarios):
            avg_values = []
            print(f"\nProcessing scenario: {scenario_name}")
            
            # For each question in this scenario
            for question_idx in range(1, num_vars + 1):
                question_name = question_types[question_idx - 1] if question_idx <= len(question_types) else f"Q{question_idx}"
                question_values = []
                
                # For each participant, find which T number corresponds to this scenario
                for _, row in filtered_df.iterrows():
                    participant_id = row['Participant ID']
                    participant_scenarios = participant_scenario_maps.get(participant_id, [])
                    
                    # Find which T number (1-4) corresponds to this scenario for this participant
                    try:
                        t_number = participant_scenarios.index(scenario_name) + 1  # +1 because T1, T2, T3, T4
                        col_name = f'T{t_number}Q{question_idx}'
                        
                        if col_name in row and pd.notna(row[col_name]):
                            value = row[col_name]
                            try:
                                if isinstance(value, str) and value.isdigit():
                                    value = float(value)
                                elif isinstance(value, (int, float)):
                                    value = float(value)
                                else:
                                    continue  # Skip invalid values
                                question_values.append(value)
                                print(f"  {participant_id} - {question_name}: {value} (from {col_name})")
                            except:
                                continue  # Skip invalid values
                    except ValueError:
                        # This participant doesn't have this scenario
                        print(f"  {participant_id} - {question_name}: scenario not found")
                        continue
                
                # Calculate average across all participants for this question in this scenario
                if question_values:
                    avg_value = np.mean(question_values)
                else:
                    avg_value = 5  # Default value
                    print(f"  → No valid responses for {question_name}, using default: {avg_value}")
                
                avg_values.append(avg_value)
            
            avg_values += avg_values[:1]  # Complete the circle
            
            # Plot the scenario
            ax.plot(angles, avg_values, 'o-', linewidth=3, label=scenario_name, 
                   color=colors[scenario_idx % len(colors)], alpha=0.8, markersize=8)
            ax.fill(angles, avg_values, alpha=0.25, color=colors[scenario_idx % len(colors)])
        
        # Customize the plot
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([])  # Remove default labels first
        ax.set_ylim(0, 10)
        ax.set_yticks([2, 4, 6, 8, 10])
        ax.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Add custom labels with higher z-order to appear in front
        for angle, label in zip(angles[:-1], question_types):
            # Calculate position slightly outside the plot area
            label_radius = 11  # Position labels outside the 0-10 scale
            x = label_radius * np.cos(angle - np.pi/2)  # Adjust for polar coordinate system
            y = label_radius * np.sin(angle - np.pi/2)
            
            ax.text(angle, label_radius, label, 
                   horizontalalignment='center', 
                   verticalalignment='center',
                   fontsize=12, fontweight='bold',
                   zorder=10,  # High z-order to appear in front
                   bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8, edgecolor='none'))
        
        # Add title
        participant_names = ", ".join(participant_ids)
        if len(participant_names) > 50:  # Truncate if too long
            participant_names = f"{len(participant_ids)} participants"
        
        ax.set_title(f'NASA TLX Workload Assessment', 
                    fontsize=14, fontweight='bold', pad=30)
        
        # Add legend
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0), fontsize=11)
        
        plt.tight_layout()
        return fig
    
    def create_combined_visualization(self, participant_ids: List[str], save_path: str = None):
        """Create combined visualization with both SUS and TLX plots."""
        # Create figure with subplots
        fig = plt.figure(figsize=(20, 12))
        
        # SUS Box Plot (top half)
        ax1 = plt.subplot(2, 1, 1)
        
        # Filter data for specified participants
        filtered_df = self.df[self.df['Participant ID'].isin(participant_ids)]
        
        if len(filtered_df) == 0:
            raise ValueError(f"No data found for participants: {participant_ids}")
        
        # Get SUS questions
        sus_questions = self.get_sus_questions()
        sus_columns = [f'Q{i}' for i in range(1, 11)]
        
        # Prepare SUS data
        sus_data = []
        for _, row in filtered_df.iterrows():
            for col in sus_columns:
                if col in row and pd.notna(row[col]):
                    try:
                        value = row[col]
                        if isinstance(value, str):
                            if ' - ' in value:
                                value = value.split(' - ')[0]
                            value = float(value)
                        sus_data.append({
                            'Participant': row['Participant ID'],
                            'Question': col,
                            'Score': value
                        })
                    except (ValueError, TypeError):
                        continue
        
        sus_df = pd.DataFrame(sus_data)
        
        # Create SUS box plot
        sns.boxplot(data=sus_df, x='Question', y='Score', ax=ax1, 
                   palette='viridis', showfliers=True)
        sns.stripplot(data=sus_df, x='Question', y='Score', ax=ax1, 
                     color='red', alpha=0.7, size=6)
        
        ax1.set_title('System Usability Score (SUS) Distribution', 
                     fontsize=14, fontweight='bold')
        ax1.set_xlabel('SUS Questions', fontsize=12)
        ax1.set_ylabel('Score (1-5)', fontsize=12)
        ax1.set_ylim(0.5, 5.5)
        ax1.grid(True, alpha=0.3, axis='y')
        
        # NASA TLX Radar Plot (bottom half)
        ax2 = plt.subplot(2, 1, 2, projection='polar')
        
        # Get TLX data for the first participant (or combine all)
        if participant_ids:
            participant_id = participant_ids[0]  # Use first participant for demo
            participant_data = self.df[self.df['Participant ID'] == participant_id]
            
            if len(participant_data) > 0:
                # Get TLX questions
                tlx_questions = self.get_tlx_questions()
                question_types = []
                for col, label in tlx_questions.items():
                    if re.match(r'T1Q\d+$', col):
                        question_types.append(label)
                
                if question_types:
                    num_vars = len(question_types)
                    angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
                    angles += angles[:1]
                    
                    # Get scenario labels
                    scenarios = self.parse_tlx_scenarios(participant_id)
                    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
                    
                    # Plot each scenario
                    for scenario_idx in range(4):
                        values = []
                        for question_idx in range(1, num_vars + 1):
                            col_name = f'T{scenario_idx + 1}Q{question_idx}'
                            if col_name in participant_data.columns:
                                value = participant_data[col_name].iloc[0]
                                if pd.notna(value):
                                    try:
                                        if isinstance(value, str) and value.isdigit():
                                            value = float(value)
                                        elif isinstance(value, (int, float)):
                                            value = float(value)
                                        else:
                                            value = 5
                                        values.append(value)
                                    except:
                                        values.append(5)
                                else:
                                    values.append(5)
                            else:
                                values.append(5)
                        
                        values += values[:1]
                        
                        scenario_label = scenarios[scenario_idx] if scenario_idx < len(scenarios) else f"Scenario {scenario_idx + 1}"
                        ax2.plot(angles, values, 'o-', linewidth=2, label=scenario_label, 
                               color=colors[scenario_idx % len(colors)], alpha=0.8)
                        ax2.fill(angles, values, alpha=0.25, color=colors[scenario_idx % len(colors)])
                    
                    ax2.set_xticks(angles[:-1])
                    ax2.set_xticklabels(question_types, fontsize=10)
                    ax2.set_ylim(0, 10)
                    ax2.set_yticks([2, 4, 6, 8, 10])
                    ax2.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=8)
                    ax2.grid(True, alpha=0.3)
                    ax2.set_title(f'NASA TLX - {participant_id}', fontsize=14, fontweight='bold', pad=20)
                    ax2.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Visualization saved to: {save_path}")
        
        return fig


def visualize_surveys(csv_path: str, participant_ids: List[str], sus_save_path: str = None, tlx_save_path: str = None):
    """Main function to create separate SUS and TLX survey visualizations."""
    visualizer = SurveyVisualizer(csv_path)
    
    print(f"Creating visualizations for participants: {participant_ids}")
    
    # Create SUS box plot
    print("Creating SUS box plot...")
    sus_fig = visualizer.create_sus_boxplots(participant_ids)
    if sus_save_path:
        sus_fig.savefig(sus_save_path, dpi=300, bbox_inches='tight')
        print(f"SUS visualization saved to: {sus_save_path}")
    
    # Create TLX radar plot
    print("Creating NASA TLX radar plot...")
    tlx_fig = visualizer.create_radar_plot(participant_ids)
    if tlx_save_path:
        tlx_fig.savefig(tlx_save_path, dpi=300, bbox_inches='tight')
        print(f"TLX visualization saved to: {tlx_save_path}")
    
    plt.show()
    return sus_fig, tlx_fig


# Example usage
if __name__ == "__main__":
    # Example participant IDs - replace with actual IDs from your data
    participant_ids = [f"Subject{i}" for i in [1,2,3,4,6,7,8,9,10,12,15,16,17]]  # Add more as needed
    
    # Create separate visualizations
    sus_fig, tlx_fig = visualize_surveys(
        csv_path="./surveys.csv", 
        participant_ids=participant_ids, 
        sus_save_path="sus_analysis.png",
        tlx_save_path="tlx_analysis.png"
    )
