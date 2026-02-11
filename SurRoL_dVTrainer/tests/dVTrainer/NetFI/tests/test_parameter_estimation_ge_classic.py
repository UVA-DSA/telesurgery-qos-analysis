from netfi.parameter_estimation.find_params_h_k import calculate_required_parameters

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
