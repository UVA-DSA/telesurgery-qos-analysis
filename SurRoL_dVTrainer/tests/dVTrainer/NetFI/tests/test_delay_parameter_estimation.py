import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from tqdm import tqdm
import os
import pandas as pd
from netfi.models.delay_model import DelayModel

def calculate_expected_delay(lower_bound, weights, lambdas):
    """
    Calculate the expected delay for a hyperexponential distribution.
    
    Args:
        lower_bound: Minimum delay (in ms)
        weights: List of weights for each exponential component
        lambdas: List of rate parameters for each exponential component
        
    Returns:
        Expected delay in ms
    """
    # Expected value of exponential distribution is 1/lambda
    # For hyperexponential, it's the weighted sum of the expected values
    expected_value = lower_bound + sum(w / l for w, l in zip(weights, lambdas))
    return expected_value

def simulate_delay(model, num_samples=100000):
    """
    Simulate delays using the model and return statistics.
    
    Args:
        model: DelayModel instance
        num_samples: Number of samples to generate
        
    Returns:
        Dictionary with delay statistics
    """
    delays = model.sample_delays(num_samples)
    
    return {
        'mean_delay': np.mean(delays),
        'median_delay': np.median(delays),
        'p95_delay': np.percentile(delays, 95),
        'p99_delay': np.percentile(delays, 99),
        'std_delay': np.std(delays),
        'delays': delays
    }

def objective_function(params, target_delay, lower_bound, min_lambda_ratio=1.5):
    """
    Objective function for optimization.
    
    Args:
        params: [weight1, lambda1, lambda2] (weight2 = 1 - weight1)
        target_delay: Target average delay
        lower_bound: Minimum delay
        min_lambda_ratio: Minimum ratio between lambda2 and lambda1
        
    Returns:
        Squared difference between achieved and target delay
    """
    weight1 = params[0]
    lambda1 = params[1]
    lambda2 = params[2]
    weight2 = 1 - weight1
    
    # Ensure lambda2 > lambda1 (for more adverse conditions)
    if lambda2 <= lambda1 * min_lambda_ratio:
        return 1e10  # Large penalty
    
    # Calculate expected delay
    expected_delay = calculate_expected_delay(lower_bound, [weight1, weight2], [lambda1, lambda2])
    
    # Return squared difference from target
    return (expected_delay - target_delay) ** 2

def estimate_parameters(
    target_delay,
    lower_bound,
    min_lambda_ratio=1.5,
    num_attempts=5,
    num_samples=100000
):
    """
    Estimate parameters for DelayModel to achieve target delay.
    
    Args:
        target_delay: Target average delay in ms
        lower_bound: Minimum delay in ms
        min_lambda_ratio: Minimum ratio between lambda2 and lambda1
        num_attempts: Number of optimization attempts with different initial points
        num_samples: Number of samples for final simulation
        
    Returns:
        Dictionary with best parameters and statistics
    """
    best_result = None
    best_obj_value = float('inf')
    
    # Define bounds for parameters
    bounds = [
        (0.1, 0.9),     # weight1 (0.1 to 0.9)
        (0.01, 1.0),    # lambda1 (0.01 to 1.0)
        (0.01, 1.0)     # lambda2 (0.01 to 1.0)
    ]
    
    # Try multiple optimization attempts with different initial points
    for attempt in tqdm(range(num_attempts), desc="Optimization attempts"):
        # Random initial point
        initial_params = [
            np.random.uniform(0.1, 0.9),  # weight1
            np.random.uniform(0.01, 0.5), # lambda1
            np.random.uniform(0.1, 1.0)   # lambda2
        ]
        
        # Optimize
        result = minimize(
            objective_function,
            initial_params,
            args=(target_delay, lower_bound, min_lambda_ratio),
            method='L-BFGS-B',
            bounds=bounds,
            options={'maxiter': 1000}
        )
        
        # Check if this is the best result so far
        if result.fun < best_obj_value:
            best_obj_value = result.fun
            best_result = result
    
    # Extract best parameters
    weight1 = best_result.x[0]
    lambda1 = best_result.x[1]
    lambda2 = best_result.x[2]
    weight2 = 1 - weight1
    
    # Create model with best parameters
    model = DelayModel(
        lower_bound=lower_bound,
        weights=[weight1, weight2],
        lambdas=[lambda1, lambda2]
    )
    
    # Simulate with best parameters
    stats = simulate_delay(model, num_samples)
    
    return {
        'best_params': {
            'lower_bound': lower_bound,
            'weights': [weight1, weight2],
            'lambdas': [lambda1, lambda2]
        },
        'expected_delay': calculate_expected_delay(lower_bound, [weight1, weight2], [lambda1, lambda2]),
        'simulated_delay': stats['mean_delay'],
        'difference': abs(stats['mean_delay'] - target_delay),
        'stats': stats,
        'optimization_result': best_result
    }

def plot_results(results, save_path=None):
    """
    Plot the results of parameter estimation.
    
    Args:
        results: Dictionary with estimation results
        save_path: Path to save the plot (if None, display the plot)
    """
    params = results['best_params']
    stats = results['stats']
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot delay distribution
    ax1.hist(stats['delays'], bins=50, density=True, alpha=0.6, color='skyblue',
             edgecolor='black', label='Empirical')
    
    # Plot theoretical PDF
    x = np.linspace(params['lower_bound'], min(300, np.max(stats['delays'])), 1000)
    model = DelayModel(params['lower_bound'], params['weights'], params['lambdas'])
    pdf_vals = model.pdf(x)
    ax1.plot(x, pdf_vals, 'r-', lw=2, label='Theoretical PDF')
    
    ax1.set_xlabel('Delay (ms)', fontsize=12)
    ax1.set_ylabel('Probability Density', fontsize=12)
    ax1.set_title('Delay Distribution', fontsize=14)
    ax1.legend()
    ax1.grid(True)
    
    # Plot statistics
    ax2.axis('off')
    stats_text = [
        "Delay Model Parameters",
        f"Lower Bound: {params['lower_bound']:.2f} ms",
        f"Weight 1: {params['weights'][0]:.3f}",
        f"Weight 2: {params['weights'][1]:.3f}",
        f"Lambda 1: {params['lambdas'][0]:.3f}",
        f"Lambda 2: {params['lambdas'][1]:.3f}",
        "",
        "Delay Statistics",
        f"Target Delay: {results['expected_delay']:.2f} ms",
        f"Simulated Mean: {stats['mean_delay']:.2f} ms",
        f"Median: {stats['median_delay']:.2f} ms",
        f"95th Percentile: {stats['p95_delay']:.2f} ms",
        f"99th Percentile: {stats['p99_delay']:.2f} ms",
        f"Standard Deviation: {stats['std_delay']:.2f} ms"
    ]
    
    ax2.text(0.1, 0.9, "\n".join(stats_text), fontsize=12, va='top',
             bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=1'))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()

def save_results_to_excel(results_dict, filename='delay_parameter_estimation_results.xlsx'):
    """Save results to Excel file"""
    
    # Convert results to DataFrame
    data = []
    for target_delay, result in results_dict.items():
        data.append({
            'Target Delay (ms)': target_delay,
            'Lower Bound (ms)': result['best_params']['lower_bound'],
            'Weight 1': result['best_params']['weights'][0],
            'Weight 2': result['best_params']['weights'][1],
            'Lambda 1': result['best_params']['lambdas'][0],
            'Lambda 2': result['best_params']['lambdas'][1],
            'Expected Delay (ms)': result['expected_delay'],
            'Simulated Delay (ms)': result['simulated_delay'],
            'Difference (ms)': result['difference'],
            'Median Delay (ms)': result['stats']['median_delay'],
            'P95 Delay (ms)': result['stats']['p95_delay'],
            'P99 Delay (ms)': result['stats']['p99_delay'],
            'Std Delay (ms)': result['stats']['std_delay']
        })
    
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print(f"\nResults saved to {filename}")

if __name__ == "__main__":
    # Create directory for plots
    plots_dir = "delay_parameter_estimation_plots"
    os.makedirs(plots_dir, exist_ok=True)
    
    # Define target delays and lower bounds
    target_delays = np.arange(50, 301, 50)  # 10ms to 300ms in 10ms increments
    lower_bounds = [0.7 * delay for delay in target_delays]  # Lower bound is 70% of target delay
    
    # Store results for all experiments
    results_dict = {}
    
    # Run experiments for each target delay and lower bound
    for lower_bound, target_delay in tqdm(zip(lower_bounds, target_delays), desc="Running experiments"):
        print(f"\nOptimizing for target delay: {target_delay}ms, lower_bound: {lower_bound}ms")
            
        results = estimate_parameters(
            target_delay=target_delay,
            lower_bound=lower_bound,
            min_lambda_ratio=1.5,
            num_attempts=3,
            num_samples=100000
        )
        
        # Store results
        key = f"{target_delay}ms_lb{lower_bound}ms"
        results_dict[key] = results
        
        # Create model with best parameters
        model = DelayModel(
            lower_bound=results['best_params']['lower_bound'],
            weights=results['best_params']['weights'],
            lambdas=results['best_params']['lambdas']
        )
        
        # Save plot to file
        plot_path = os.path.join(plots_dir, f'delay_{target_delay}ms_lb{lower_bound}ms.png')
        plot_results(results, save_path=plot_path)
        
        # Print current results
        print(f"\nResults for {target_delay}ms target delay, {lower_bound}ms lower bound:")
        print(f"Weight 1: {results['best_params']['weights'][0]:.3f}")
        print(f"Weight 2: {results['best_params']['weights'][1]:.3f}")
        print(f"Lambda 1: {results['best_params']['lambdas'][0]:.3f}")
        print(f"Lambda 2: {results['best_params']['lambdas'][1]:.3f}")
        print(f"Expected delay: {results['expected_delay']:.2f}ms")
        print(f"Simulated delay: {results['simulated_delay']:.2f}ms")
        print(f"Difference: {results['difference']:.2f}ms")

# Save all results to Excel
save_results_to_excel(results_dict)

print("\nAll experiments completed!")
print(f"Results saved to delay_parameter_estimation_results.xlsx")
print(f"Plots saved to {plots_dir}/") 