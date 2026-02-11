import numpy as np
from scipy.optimize import minimize
from tqdm import tqdm
import csv
import time
from netfi.models.ge_classic import GEClassicModel

def simulate_ge_classic(q, r, k, h, num_samples=100000):
    """Simulate GE Classic model and return loss rate + average BLL"""
    state_params = {
        'Good': {
            'transitions': {'Good': 1 - q, 'Bad': q},
            'params': {'k': k}
        },
        'Bad': {
            'transitions': {'Good': r, 'Bad': 1 - r},
            'params': {'h': h}
        }
    }
    
    model = GEClassicModel(state_params)
    total_lost = 0
    current_burst = 0
    burst_lengths = []
    
    for _ in range(num_samples):
        if model.process_packet():
            total_lost += 1
            current_burst += 1
        else:
            if current_burst > 0:
                burst_lengths.append(current_burst)
                current_burst = 0
                
    # Add final burst if any
    if current_burst > 0:
        burst_lengths.append(current_burst)
    
    loss_rate = total_lost / num_samples
    avg_bll = np.mean(burst_lengths) if burst_lengths else 0
    return loss_rate, avg_bll

def calculate_required_parameters(target_loss, target_bll, q, r, num_samples=100000):
    """Find optimal h and k parameters using numerical optimization"""
    def objective(params):
        k, h = params
        if not (0 <= k <= 1 and 0 <= h <= 1):
            return np.inf  # Penalize invalid parameters
        
        # Fast approximation with smaller sample size
        loss_rate, avg_bll = simulate_ge_classic(q, r, k, h, num_samples=10000)
        
        # Combined error metric with dynamic weighting
        loss_error = (loss_rate - target_loss) ** 2
        bll_error = ((avg_bll - target_bll) / max(target_bll, 1)) ** 2  # Normalized
        return loss_error + bll_error

    # Theoretical initialization using GE model equations
    # Steady-state probability of being in Bad state: p_b = q / (q + r)
    p_b = q / (q + r) if (q + r) > 0 else 0.0
    
    # Theoretical k and h from desired loss rate and BLL
    # Loss rate = p_b*(1-h) + (1-p_b)*(1-k)
    # Average BLL = 1 / (1 - (1-r)*(1-h))
    try:
        # Solve for h from BLL equation
        h_theory = 1 - (1 - (1/target_bll)) / (1 - r)
        h_theory = np.clip(h_theory, 0.01, 0.99)
        
        # Solve for k from loss rate equation
        k_theory = 1 - (target_loss - p_b*(1 - h_theory)) / (1 - p_b)
        k_theory = np.clip(k_theory, 0.01, 0.99)
        
        initial_guess = [k_theory, h_theory]
    except:
        # Fallback to previous heuristic if theoretical values fail
        initial_guess = [0.9, 0.1]

    bounds = [(0.01, 0.99), (0.01, 0.99)]  # Keep away from edges
    
    result = minimize(
        objective,
        initial_guess,
        method='L-BFGS-B',
        bounds=bounds,
        options={'maxiter': 30, 'disp': False}  # Reduced iterations needed
    )
    
    if not result.success:
        raise ValueError("Optimization failed to converge")
        
    # Validate with full simulation
    final_k, final_h = result.x
    final_loss, final_bll = simulate_ge_classic(q, r, final_k, final_h, num_samples)
    
    return {
        'k': final_k,
        'h': final_h,
        'actual_loss': final_loss,
        'actual_bll': final_bll
    }

def process_calibration(input_csv, output_csv, num_samples=100000):
    """Batch process parameter optimization from CSV input"""
    with open(input_csv, 'r') as infile, open(output_csv, 'w', newline='') as outfile:
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=[
            'target_loss', 'target_bll', 'q', 'r',
            'calculated_k', 'calculated_h',
            'actual_loss', 'actual_bll', 'computation_time'
        ])
        writer.writeheader()
        
        for row in tqdm(list(reader), desc="Processing calibrations"):
            start_time = time.time()
            
            try:
                params = calculate_required_parameters(
                    target_loss=float(row['target_loss']),
                    target_bll=float(row['target_bll']),
                    q=float(row['q']),
                    r=float(row['r']),
                    num_samples=num_samples
                )
                
                writer.writerow({
                    'target_loss': row['target_loss'],
                    'target_bll': row['target_bll'],
                    'q': row['q'],
                    'r': row['r'],
                    'calculated_k': round(params['k'], 4),
                    'calculated_h': round(params['h'], 4),
                    'actual_loss': round(params['actual_loss'], 4),
                    'actual_bll': round(params['actual_bll'], 2),
                    'computation_time': round(time.time() - start_time, 2)
                })
                
            except Exception as e:
                print(f"Error processing row {row}: {str(e)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='GE Classic Parameter Optimizer')
    parser.add_argument('--samples', type=int, default=100000,
                        help='Number of samples for final validation')
    parser.add_argument('--target-loss', type=float, required=True,
                        help='Target loss rate (e.g., 0.1 for 10%)')
    parser.add_argument('--target-bll', type=float, required=True,
                        help='Target average burst loss length (e.g., 5.0)')
    parser.add_argument('--q', type=float, required=True,
                        help='Probability of transitioning from Good to Bad state')
    parser.add_argument('--r', type=float, required=True,
                        help='Probability of transitioning from Bad to Good state')
    args = parser.parse_args()
    
    # Calculate the required parameters
    params = calculate_required_parameters(
        target_loss=args.target_loss,
        target_bll=args.target_bll,
        q=args.q,
        r=args.r,
        num_samples=args.samples
    )
    
    # Print the results
    print("Calculated Parameters:")
    print(f"k = {params['k']:.4f}")
    print(f"h = {params['h']:.4f}")
    print(f"Actual Loss Rate: {params['actual_loss']:.4%}")
    print(f"Actual Average BLL: {params['actual_bll']:.2f}")