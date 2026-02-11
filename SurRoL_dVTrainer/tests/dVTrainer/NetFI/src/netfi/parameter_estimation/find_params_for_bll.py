import csv
import time
import numpy as np
from scipy.optimize import minimize_scalar
from tqdm import tqdm
import argparse

from netfi.models.utils import pareto_type_ii_sample

def calculate_required_parameters(target_avg_bll, fixed_alpha=None, fixed_lambda=None, num_samples=100000):
    """Find parameters that achieve target average Backlog Loss Length (BLL)"""
    def bll_error(param):
        if fixed_alpha is not None:
            alpha = fixed_alpha
            lambda_param = param
        else:
            alpha = param
            lambda_param = fixed_lambda

        # Simulate to get average BLL
        total_bll = 0
        bll_count = 0
        for _ in tqdm(range(num_samples), desc="Calibrating parameters", leave=False):
            bll = int(pareto_type_ii_sample(alpha, lambda_param, size=1)[0])
            if bll > 0:
                total_bll += bll
                bll_count += 1
        
        avg_bll = total_bll / bll_count if bll_count > 0 else 0
        return abs(avg_bll - target_avg_bll)

    if (fixed_alpha is None) == (fixed_lambda is None):
        raise ValueError("Must fix exactly one parameter (alpha or lambda)")

    if fixed_alpha is not None:
        result = minimize_scalar(bll_error, bounds=(0.1, 100), method='bounded')
        return {'alpha': fixed_alpha, 'lambda': result.x}
    else:
        result = minimize_scalar(bll_error, bounds=(1.1, 100), method='bounded')
        return {'alpha': result.x, 'lambda': fixed_lambda}

def simulate_bll_rate(alpha, lambda_param, num_samples=100000):
    """Simulate actual BLL and loss rate"""
    total_packets = 0
    dropped_packets = 0
    total_bll = 0
    bll_count = 0
    
    for _ in tqdm(range(num_samples), desc="Simulating BLL", leave=False):
        bll = int(pareto_type_ii_sample(alpha, lambda_param, size=1)[0])
        if bll > 0:
            total_bll += bll
            bll_count += 1
            dropped_packets += bll
            total_packets += bll + 1
        else:
            total_packets += 1
    
    avg_bll = total_bll / bll_count if bll_count > 0 else 0
    actual_loss = dropped_packets / total_packets if total_packets > 0 else 0
    return avg_bll, actual_loss

def process_calibration(input_csv, output_csv, num_samples):
    with open(input_csv, 'r') as infile, open(output_csv, 'w', newline='') as outfile:
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=[
            'target_avg_bll', 'fixed_param', 'param_value',
            'calculated_alpha', 'calculated_lambda',
            'actual_avg_bll', 'loss_rate', 'computation_time'
        ])
        writer.writeheader()
        
        for row in tqdm(list(reader), desc="Processing rows"):
            start_time = time.time()
            target = float(row['target_avg_bll'])
            fixed_param = row['fixed_param']
            param_value = float(row['param_value'])
            
            # Calculate parameters
            params = calculate_required_parameters(
                target_avg_bll=target,
                fixed_alpha=param_value if fixed_param == 'alpha' else None,
                fixed_lambda=param_value if fixed_param == 'lambda' else None,
                num_samples=num_samples
            )
            
            # Simulate actual results
            actual_bll, loss_rate = simulate_bll_rate(
                params['alpha'], 
                params['lambda'],
                num_samples=num_samples
            )
            
            # Write results
            writer.writerow({
                'target_avg_bll': target,
                'fixed_param': fixed_param,
                'param_value': param_value,
                'calculated_alpha': round(params['alpha'], 4),
                'calculated_lambda': round(params['lambda'], 4),
                'actual_avg_bll': round(actual_bll, 2),
                'loss_rate': round(loss_rate, 4),
                'computation_time': round(time.time() - start_time, 2)
            })

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='BLL Parameter Calibrator')
    parser.add_argument('--samples', type=int, default=100000, help='Number of samples per simulation')
    args = parser.parse_args()
    
    process_calibration('./input_params.csv', 'calibration_results.csv', args.samples)