import numpy as np
from pyge.models import CommunicationLossModel
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from tqdm import tqdm
import os
import pandas as pd

def simulate_loss_rate(model, num_packets=100000):
    """
    Simulate packet loss using the model and calculate the loss rate.
    
    Args:
        model: CommunicationLossModel instance
        num_packets: Number of packets to simulate
    
    Returns:
        Loss rate (fraction of packets lost)
    """
    lost_packets = 0
    
    for _ in tqdm(range(num_packets), desc="Simulating packets", leave=False):
        if model.should_drop():
            lost_packets += 1
    
    return lost_packets / num_packets

def objective_function(loss_prob, target_loss_rate, min_loss_length, max_loss_length, 
                      cooldown_period, num_packets=100000, num_simulations=3):
    """
    Objective function that averages over multiple simulation runs to reduce noise.
    
    Args:
        loss_prob: Probability of entering a loss period
        target_loss_rate: Target loss rate to achieve
        min_loss_length: Minimum length of a loss period
        max_loss_length: Maximum length of a loss period
        cooldown_period: Cooldown period after a loss period
        num_packets: Number of packets to simulate
        num_simulations: Number of simulation runs to average over
    
    Returns:
        Squared difference between achieved and target loss rate
    """
    loss_rates = []
    
    for _ in range(num_simulations):
        # Create model with current parameters
        model = CommunicationLossModel({
            'loss_prob': loss_prob,
            'min_loss_length': min_loss_length,
            'max_loss_length': max_loss_length,
            'cooldown_period': cooldown_period
        })
        
        # Simulate and calculate loss rate
        loss_rate = simulate_loss_rate(model, num_packets)
        loss_rates.append(loss_rate)
    
    avg_loss_rate = np.mean(loss_rates)
    
    # Return squared difference from target loss rate
    return (avg_loss_rate - target_loss_rate) ** 2

def estimate_loss_probability(
    target_loss_rate,
    min_loss_length=1,
    max_loss_length=5,
    cooldown_period=10,
    num_packets=100000,
    num_simulations=3
):
    """
    Estimate the loss probability parameter to achieve a target loss rate.
    
    Args:
        target_loss_rate: Target loss rate to achieve (0.0-1.0)
        min_loss_length: Minimum length of a loss period
        max_loss_length: Maximum length of a loss period
        cooldown_period: Cooldown period after a loss period
        num_packets: Number of packets to simulate
        num_simulations: Number of simulation runs to average over
    
    Returns:
        Dictionary with best parameters and statistics
    """
    # Define bounds for loss_prob (must be between 0 and 1)
    bounds = [(0.0, 1.0)]
    
    # Objective function wrapper for minimize
    def obj_wrapper(loss_prob):
        return objective_function(
            loss_prob[0], 
            target_loss_rate, 
            min_loss_length, 
            max_loss_length, 
            cooldown_period, 
            num_packets, 
            num_simulations
        )
    
    # Run multiple optimization attempts with different initial points
    best_result = None
    best_loss_prob = None
    best_obj_value = float('inf')
    
    # Try different initial points
    initial_points = [0.01, 0.05, 0.1, 0.2, 0.5]
    
    for initial_point in tqdm(initial_points, desc="Optimization attempts"):
        result = minimize(
            obj_wrapper,
            x0=[initial_point],
            bounds=bounds,
            method='L-BFGS-B',
            options={'disp': False}
        )
        
        if result.fun < best_obj_value:
            best_result = result
            best_loss_prob = result.x[0]
            best_obj_value = result.fun
    
    # Evaluate the final performance with more simulations for robustness
    final_simulations = 10
    loss_rates = []
    
    for _ in range(final_simulations):
        model = CommunicationLossModel({
            'loss_prob': best_loss_prob,
            'min_loss_length': min_loss_length,
            'max_loss_length': max_loss_length,
            'cooldown_period': cooldown_period
        })
        
        loss_rate = simulate_loss_rate(model, num_packets)
        loss_rates.append(loss_rate)
    
    avg_loss_rate = np.mean(loss_rates)
    diff = abs(avg_loss_rate - target_loss_rate)
    
    return {
        'best_params': {
            'loss_prob': best_loss_prob,
            'min_loss_length': min_loss_length,
            'max_loss_length': max_loss_length,
            'cooldown_period': cooldown_period
        },
        'best_loss_rate': avg_loss_rate,
        'min_diff': diff,
        'optimization_result': best_result
    }

def plot_results(model, num_packets=100000, bins=50):
    """
    Plot the loss pattern and statistics.
    
    Args:
        model: CommunicationLossModel instance
        num_packets: Number of packets to simulate
        bins: Number of bins for histogram
    """
    # Simulate packet loss
    lost_packets = []
    loss_periods = []
    current_period = 0
    
    for i in tqdm(range(num_packets), desc="Simulating packets for plot", leave=False):
        if model.should_drop():
            lost_packets.append(i)
            current_period += 1
        elif current_period > 0:
            loss_periods.append(current_period)
            current_period = 0
    
    if current_period > 0:
        loss_periods.append(current_period)
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot 1: Loss pattern
    ax1.set_title('Packet Loss Pattern')
    ax1.set_xlabel('Packet Number')
    ax1.set_ylabel('Lost')
    
    # Create a binary array for lost packets
    lost_mask = np.zeros(num_packets, dtype=bool)
    lost_mask[lost_packets] = True
    
    # Plot as a thin line
    ax1.plot(range(num_packets), lost_mask, 'r-', linewidth=0.5)
    ax1.set_ylim(-0.1, 1.1)
    ax1.set_yticks([0, 1])
    ax1.set_yticklabels(['Received', 'Lost'])
    
    # Plot 2: Loss period length histogram
    if loss_periods:
        ax2.hist(loss_periods, bins=min(bins, max(loss_periods)), 
                color='skyblue', edgecolor='black', linewidth=0.5, density=True)
        ax2.set_title('Loss Period Length Distribution')
        ax2.set_xlabel('Loss Period Length (packets)')
        ax2.set_ylabel('Density')
        
        # Add text with statistics
        mean_length = np.mean(loss_periods)
        loss_rate = len(lost_packets) / num_packets
        stats_text = f'Mean Length: {mean_length:.2f}\nLoss Rate: {loss_rate:.2%}'
        ax2.text(0.95, 0.95, stats_text, transform=ax2.transAxes, 
                ha='right', va='top', bbox=dict(facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.show()

def save_results_to_excel(results_dict, filename='communication_loss_parameter_estimation_results.xlsx'):
    """Save results to Excel file"""
    
    # Convert results to DataFrame
    data = []
    for target_loss, result in results_dict.items():
        data.append({
            'Target Loss Rate': target_loss,
            'Loss Probability': result['best_params']['loss_prob'],
            'Min Loss Length': result['best_params']['min_loss_length'],
            'Max Loss Length': result['best_params']['max_loss_length'],
            'Cooldown Period': result['best_params']['cooldown_period'],
            'Achieved Loss Rate': result['best_loss_rate'],
            'Difference from Target': result['min_diff']
        })
    
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print(f"\nResults saved to {filename}")

if __name__ == "__main__":
    # Create directory for plots
    plots_dir = "communication_loss_parameter_estimation_plots"
    os.makedirs(plots_dir, exist_ok=True)
    
    # Define target loss rates
    target_losses = np.arange(0.01, 1, 0.05)  # 1% to 20% in 1% increments
    
    # Define loss length configurations
    loss_length_configs = [
        {'min': 0, 'max': 5000, 'cooldown': 5000},
        {'min': 0, 'max': 2000, 'cooldown': 5000},
        {'min': 0, 'max': 2000, 'cooldown': 2000}
    ]
    
    # Store results for all experiments
    results_dict = {}
    
    # Run experiments for each target loss rate and loss length configuration
    for config in loss_length_configs:
        config_key = f"min{config['min']}_max{config['max']}_cooldown{config['cooldown']}"
        results_dict[config_key] = {}
        
        for target_loss in tqdm(target_losses, desc=f"Running experiments for {config_key}"):
            print(f"\nOptimizing for target loss rate: {target_loss:.2%}")
            
            results = estimate_loss_probability(
                target_loss_rate=target_loss,
                min_loss_length=config['min'],
                max_loss_length=config['max'],
                cooldown_period=config['cooldown'],
                num_packets=100000,
                num_simulations=3
            )
            
            # Store results
            results_dict[config_key][target_loss] = results
            
            # Create model with best parameters
            model = CommunicationLossModel({
                'loss_prob': results['best_params']['loss_prob'],
                'min_loss_length': results['best_params']['min_loss_length'],
                'max_loss_length': results['best_params']['max_loss_length'],
                'cooldown_period': results['best_params']['cooldown_period']
            })
            
            # Simulate and plot results
            print(f"Generating visualization for {target_loss:.2%} target loss...")
            plt.figure(figsize=(12, 10))
            plot_results(model, 100000)
            plt.savefig(os.path.join(plots_dir, f'loss_{config_key}_{target_loss:.2f}.png'), 
                       dpi=300, bbox_inches='tight')
            plt.close()
            
            # Print current results
            print(f"\nResults for {target_loss:.2%} target loss:")
            print(f"Loss Probability: {results['best_params']['loss_prob']:.6f}")
            print(f"Achieved loss rate: {results['best_loss_rate']:.3f}")
            print(f"Difference from target: {results['min_diff']:.3f}")
    
    # Save all results to Excel
    save_results_to_excel(results_dict)
    
    print("\nAll experiments completed!")
    print(f"Results saved to communication_loss_parameter_estimation_results.xlsx")
    print(f"Plots saved to {plots_dir}/") 