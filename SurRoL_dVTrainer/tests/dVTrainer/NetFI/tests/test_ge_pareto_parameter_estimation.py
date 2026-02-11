import numpy as np
from netfi.models import GEParetoBLLModel
import matplotlib.pyplot as plt
from typing import Tuple, Dict
import time
from scipy.optimize import minimize
from tqdm import tqdm
import os
import pandas as pd

def create_state_params(p_gb: float, p_bg: float, alpha_good: float, alpha_bad: float, 
                       lambda_good: float, lambda_bad: float) -> dict:
    """
    Create state parameters dictionary for GEParetoBLLModel.
    
    Args:
        p_gb: Probability of transitioning from Good to Bad
        p_bg: Probability of transitioning from Bad to Good
        alpha_good: Shape parameter for Good state
        alpha_bad: Shape parameter for Bad state
        lambda_good: Scale parameter for Good state
        lambda_bad: Scale parameter for Bad state
    
    Returns:
        Dictionary of state parameters
    """
    return {
        "Good": {
            "transitions": {
                "Good": 1 - p_gb,
                "Bad": p_gb
            },
            "distribution": "pareto",
            "params": {
                "alpha": alpha_good,
                "lambda": lambda_good
            }
        },
        "Bad": {
            "transitions": {
                "Good": p_bg,
                "Bad": 1 - p_bg
            },
            "distribution": "pareto",
            "params": {
                "alpha": alpha_bad,
                "lambda": lambda_bad
            }
        }
    }

def simulate_packet_loss(model: GEParetoBLLModel, num_packets: int) -> list:
    """
    Simulate packet loss using the model.
    
    Args:
        model: GEParetoBLLModel instance
        num_packets: Number of packets to simulate
    
    Returns:
        List of lost packet indices
    """
    lost_packets = []
    
    for packet in tqdm(range(num_packets), desc="Simulating packets", leave=False):
        if model.should_drop():
            lost_packets.append(packet)
    
    return lost_packets

def simulate_packet_loss_with_states(model: GEParetoBLLModel, num_packets: int) -> Tuple[list, list]:
    """
    Simulate packet loss using the model and track states.
    
    Args:
        model: GEParetoBLLModel instance
        num_packets: Number of packets to simulate
    
    Returns:
        Tuple of (lost_packets list, states list)
    """
    lost_packets = []
    states = []
    
    for packet in tqdm(range(num_packets), desc="Simulating packets", leave=False):
        # Record current state before processing
        states.append(model.current_state)
        if model.should_drop():
            lost_packets.append(packet)
    
    return lost_packets, states

def plot_state_timeline(states: list, lost_packets: list, num_packets: int):
    """
    Plot the state timeline with color bars and burst loss length histogram.
    
    Args:
        states: List of states at each packet
        lost_packets: List of lost packet indices
        num_packets: Total number of packets
    """
    # Create figure with three subplots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 10), height_ratios=[1, 2, 1])
    
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
    ax1.set_title('Model State Timeline')
    
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
        ax3.set_title('Burst Length Distribution')
        ax3.set_xlabel('Burst Length (packets)')
        ax3.set_ylabel('Density')
        
        # Add text with statistics
        mean_bll = np.mean(burst_lengths)
        loss_rate = len(lost_packets) / num_packets
        stats_text = f'Mean BLL: {mean_bll:.2f}\nLoss Rate: {loss_rate:.2%}'
        ax3.text(0.95, 0.95, stats_text, transform=ax3.transAxes, 
                ha='right', va='top', bbox=dict(facecolor='white', alpha=0.8))
    
    # Plot lost packets as thin rectangles
    lost_mask = np.zeros(num_packets, dtype=bool)
    lost_mask[lost_packets] = True
    
    # Create a grid of thin rectangles (like a progress bar)
    rectangle_height = 0.1  # Make rectangles much thinner
    y_position = (1 - rectangle_height) / 2  # Center the rectangles vertically
    
    for i in range(num_packets):
        color = '#d63031' if lost_mask[i] else '#00b894'  # Soft red and green
        ax2.add_patch(plt.Rectangle((i, y_position), 1, rectangle_height, 
                                  facecolor=color, edgecolor='none'))
    
    ax2.set_title('Lost Packets')
    ax2.set_xlabel('Packet Number')
    ax2.set_ylim(0, 1)
    ax2.set_xlim(0, num_packets)
    ax2.set_yticks([])  # Remove y-axis ticks since we're using rectangles
    
    plt.tight_layout()
    plt.show()

import numpy as np
from scipy.optimize import differential_evolution

def objective_function(params: np.ndarray, target_loss_rate: float, p_gb: float, p_bg: float, num_packets: int, num_simulations: int = 3) -> float:
    """
    Objective function that averages over multiple simulation runs to reduce noise.
    """
    alpha_good, alpha_bad, lambda_good, lambda_bad = params
    loss_rates = []
    for _ in range(num_simulations):
        # Create state parameters dictionary
        state_params = create_state_params(p_gb, p_bg, alpha_good, alpha_bad, lambda_good, lambda_bad)
        # Initialize model with current parameters
        model = GEParetoBLLModel(state_params)
        # Simulate packet loss and calculate loss rate
        lost_packets = simulate_packet_loss(model, num_packets)
        loss_rate = len(lost_packets) / num_packets
        loss_rates.append(loss_rate)
    avg_loss_rate = np.mean(loss_rates)
    # Return squared difference from target loss rate
    return (avg_loss_rate - target_loss_rate) ** 2

def estimate_parameters(
    target_loss_rate: float,
    p_gb: float = 0.1,
    p_bg: float = 0.2,
    num_packets: int = 100000,
    num_simulations: int = 3
) -> dict:
    """
    Estimate parameters using differential evolution for a robust search over the parameter space.
    """
    # Define bounds for parameters: (alpha_good, alpha_bad, lambda_good, lambda_bad)
    bounds = [
        (1.1, 5.0),  # alpha_good
        (1.1, 5.0),  # alpha_bad
        (0.1, 20.0), # lambda_good
        (0.1, 20.0)  # lambda_bad
    ]

    # Objective function wrapper for differential evolution
    def obj_wrapper(params):
        return objective_function(params, target_loss_rate, p_gb, p_bg, num_packets, num_simulations)
    
    print(f"Starting differential evolution for target loss rate: {target_loss_rate}")
    result = differential_evolution(
        obj_wrapper,
        bounds,
        maxiter=3,  # Increased iteration limit for a better search TODO
        polish=True,
        disp=True  # Display convergence messages
    )
    
    best_params = result.x

    # Evaluate the final performance with more simulations for robustness
    final_simulations = 10
    loss_rates = []
    for _ in range(final_simulations):
        state_params = create_state_params(p_gb, p_bg, best_params[0], best_params[1], best_params[2], best_params[3])
        model = GEParetoBLLModel(state_params)
        lost_packets = simulate_packet_loss(model, num_packets)
        loss_rate = len(lost_packets) / num_packets
        loss_rates.append(loss_rate)
    avg_loss_rate = np.mean(loss_rates)
    diff = abs(avg_loss_rate - target_loss_rate)
    
    return {
        'best_params': {
            'alpha_good': best_params[0],
            'alpha_bad': best_params[1],
            'lambda_good': best_params[2],
            'lambda_bad': best_params[3]
        },
        'best_loss_rate': avg_loss_rate,
        'min_diff': diff,
        'optimization_result': result
    }

def save_results_to_excel(results_dict, filename='parameter_estimation_results.xlsx'):
    """Save results to Excel file"""
    
    # Convert results to DataFrame
    data = []
    for target_loss, result in results_dict.items():
        data.append({
            'Target Loss Rate': target_loss,
            'Alpha Good': result['best_params']['alpha_good'],
            'Alpha Bad': result['best_params']['alpha_bad'],
            'Lambda Good': result['best_params']['lambda_good'],
            'Lambda Bad': result['best_params']['lambda_bad'],
            'Achieved Loss Rate': result['best_loss_rate'],
            'Difference from Target': result['min_diff'],
            'p_gb': result['p_gb'],
            'p_bg': result['p_bg']
        })
    
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print(f"\nResults saved to {filename}")

if __name__ == "__main__":
    # Create directory for plots
    plots_dir = "parameter_estimation_plots"
    os.makedirs(plots_dir, exist_ok=True)
    
    # Define target loss rates
    target_losses = np.arange(0.05, 1.00, 0.05)  # 5% to 95% in 5% increments
    
    # Store results for all experiments
    results_dict = {}
    
    # Fixed transition probabilities
    p_gb = 0.05  # 10% chance of going from Good to Bad
    p_bg = 0.1  # 20% chance of going from Bad to Good
    
    # Run experiments for each target loss rate
    for target_loss in tqdm(target_losses, desc="Running experiments"):
        print(f"\nOptimizing for target loss rate: {target_loss:.2%}")
        
        results = estimate_parameters(
            target_loss_rate=target_loss,
            p_gb=p_gb,
            p_bg=p_bg,
            num_packets=100000,
            num_simulations=3
        )
        
        # Store results
        results_dict[target_loss] = {
            'best_params': results['best_params'],
            'best_loss_rate': results['best_loss_rate'],
            'min_diff': results['min_diff'],
            'p_gb': p_gb,
            'p_bg': p_bg
        }
        
        # Create model with best parameters
        state_params = create_state_params(
            p_gb=p_gb,
            p_bg=p_bg,
            alpha_good=results['best_params']['alpha_good'],
            alpha_bad=results['best_params']['alpha_bad'],
            lambda_good=results['best_params']['lambda_good'],
            lambda_bad=results['best_params']['lambda_bad']
        )
        model = GEParetoBLLModel(state_params)
        
        # Simulate and plot results
        print(f"Generating visualization for {target_loss:.2%} target loss...")
        lost_packets, states = simulate_packet_loss_with_states(model, 100000)
        
        # Save plot to file
        plt.figure(figsize=(15, 10))
        plot_state_timeline(states, lost_packets, 100000)
        plt.savefig(os.path.join(plots_dir, f'loss_{target_loss:.2f}.png'), 
                   dpi=300, bbox_inches='tight')
        plt.close()
        
        # Print current results
        print(f"\nResults for {target_loss:.2%} target loss:")
        print(f"Alpha Good: {results['best_params']['alpha_good']:.3f}")
        print(f"Alpha Bad: {results['best_params']['alpha_bad']:.3f}")
        print(f"Lambda Good: {results['best_params']['lambda_good']:.3f}")
        print(f"Lambda Bad: {results['best_params']['lambda_bad']:.3f}")
        print(f"Achieved loss rate: {results['best_loss_rate']:.3f}")
        print(f"Difference from target: {results['min_diff']:.3f}")
    
    # Save all results to Excel
    save_results_to_excel(results_dict)
    
    print("\nAll experiments completed!")
    print(f"Results saved to parameter_estimation_results.xlsx")
    print(f"Plots saved to {plots_dir}/") 