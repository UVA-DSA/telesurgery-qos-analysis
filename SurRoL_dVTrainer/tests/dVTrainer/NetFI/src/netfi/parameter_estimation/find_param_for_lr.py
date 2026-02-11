import csv
import time
import numpy as np
from scipy.optimize import minimize_scalar

from netfi.models.utils import pareto_type_ii_sample


def calculate_required_parameters(target_loss_rate, fixed_alpha=None, fixed_lambda=None, tolerance=1e-4):
    """
    More robust parameter calculation accounting for integer BLL conversion.
    Uses numerical optimization to find parameters that achieve actual loss rate.
    """
    def loss_rate_error(param):
        if fixed_alpha is not None:
            alpha = fixed_alpha
            lambda_param = param
        else:
            alpha = param
            lambda_param = fixed_lambda

        # Simulate expected loss rate with integer conversion
        total = 0
        dropped = 0
        num_samples = 100000  # Large sample for accurate estimation
        for _ in range(num_samples):
            bll = int(pareto_type_ii_sample(alpha, lambda_param, size=1)[0])
            total += bll + 1  # BLL dropped + 1 successful
            dropped += bll
        
        actual_loss = dropped / (total)
        return abs(actual_loss - target_loss_rate)

    if (fixed_alpha is None) == (fixed_lambda is None):
        raise ValueError("Must fix exactly one parameter (alpha or lambda)")

    # Numerical optimization to find best parameter
    if fixed_alpha is not None:
        result = minimize_scalar(loss_rate_error, bounds=(0.1, 100), method='bounded')
        return {'alpha': fixed_alpha, 'lambda': result.x}
    else:
        result = minimize_scalar(loss_rate_error, bounds=(1.1, 100), method='bounded')
        return {'alpha': result.x, 'lambda': fixed_lambda}

def simulate_loss_rate(alpha, lambda_param, num_samples=100000):
    """Simulate actual loss rate with integer BLL conversion"""
    total_packets = 0
    dropped_packets = 0
    total_bll = 0
    bll_count = 0
    
    for _ in range(num_samples):
        bll = int(pareto_type_ii_sample(alpha, lambda_param, size=1)[0])
        if bll > 0:
            total_bll += bll
            bll_count += 1
            dropped_packets += bll
            total_packets += bll + 1  # Include the successful packet
        else:
            total_packets += 1
    
    actual_loss = dropped_packets / total_packets if total_packets > 0 else 0
    avg_bll = total_bll / bll_count if bll_count > 0 else 0
    return actual_loss, avg_bll

def process_calibration(input_csv, output_csv):
    with open(input_csv, 'r') as infile, open(output_csv, 'w', newline='') as outfile:
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=[
            'target_loss_rate', 'fixed_param', 'param_value',
            'calculated_alpha', 'calculated_lambda',
            'actual_loss_rate', 'avg_bll', 'computation_time'
        ])
        writer.writeheader()
        
        for row in reader:
            start_time = time.time()
            target = float(row['target_loss_rate'])
            fixed_param = row['fixed_param']
            param_value = float(row['param_value'])
            
            # Calculate parameters
            if fixed_param == 'alpha':
                params = calculate_required_parameters(
                    target_loss_rate=target,
                    fixed_alpha=param_value
                )
            else:
                params = calculate_required_parameters(
                    target_loss_rate=target,
                    fixed_lambda=param_value
                )
            
            # Simulate actual results
            actual_loss, avg_bll = simulate_loss_rate(
                params['alpha'], 
                params['lambda']
            )
            
            # Write results
            writer.writerow({
                'target_loss_rate': target,
                'fixed_param': fixed_param,
                'param_value': param_value,
                'calculated_alpha': round(params['alpha'], 4),
                'calculated_lambda': round(params['lambda'], 4),
                'actual_loss_rate': round(actual_loss, 4),
                'avg_bll': round(avg_bll, 2),
                'computation_time': round(time.time() - start_time, 2)
            })

if __name__ == "__main__":
    process_calibration('input_params.csv', 'calibration_results.csv')