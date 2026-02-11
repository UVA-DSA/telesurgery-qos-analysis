import argparse
from .find_param_for_lr import calculate_required_parameters as lr_calculator
from .find_param_for_lr import simulate_loss_rate as lr_simulator
from .find_params_for_bll import calculate_required_parameters as bll_calculator
from .find_params_for_bll import simulate_bll_rate as bll_simulator

def main():
    parser = argparse.ArgumentParser(
        description='GE Model Parameter Estimator',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--target-type', required=True, choices=['loss_rate', 'bll'],
                      help='Type of target metric to optimize')
    parser.add_argument('--target-value', type=float, required=True,
                      help='Desired value for the target metric')
    parser.add_argument('--fixed-param', required=True, choices=['alpha', 'lambda'],
                      help='Which parameter to fix during estimation')
    parser.add_argument('--fixed-value', type=float, required=True,
                      help='Value for the fixed parameter')
    parser.add_argument('--samples', type=int, default=100000,
                      help='Number of samples for empirical validation')

    args = parser.parse_args()

    try:
        if args.target_type == 'loss_rate':
            # Calculate parameters for loss rate
            params = lr_calculator(
                target_loss_rate=args.target_value,
                fixed_alpha=args.fixed_value if args.fixed_param == 'alpha' else None,
                fixed_lambda=args.fixed_value if args.fixed_param == 'lambda' else None
            )
            
            # Validate with simulation
            actual_loss, avg_bll = lr_simulator(params['alpha'], params['lambda'], args.samples)
            
            print(f"\nEstimated parameters for {args.target_value} loss rate:")
            print(f"Fixed {args.fixed_param}: {args.fixed_value}")
            print(f"Calculated alpha: {params['alpha']:.4f}")
            print(f"Calculated lambda: {params['lambda']:.4f}")
            print(f"\nEmpirical validation ({args.samples} packets):")
            print(f"Actual loss rate: {actual_loss:.4f}")
            print(f"Average BLL: {avg_bll:.2f}")

        elif args.target_type == 'bll':
            # Calculate parameters for BLL
            params = bll_calculator(
                target_avg_bll=args.target_value,
                fixed_alpha=args.fixed_value if args.fixed_param == 'alpha' else None,
                fixed_lambda=args.fixed_value if args.fixed_param == 'lambda' else None
            )
            
            # Validate with simulation
            actual_bll, loss_rate = bll_simulator(params['alpha'], params['lambda'], args.samples)
            
            print(f"\nEstimated parameters for {args.target_value} average BLL:")
            print(f"Fixed {args.fixed_param}: {args.fixed_value}")
            print(f"Calculated alpha: {params['alpha']:.4f}")
            print(f"Calculated lambda: {params['lambda']:.4f}")
            print(f"\nEmpirical validation ({args.samples} packets):")
            print(f"Actual average BLL: {actual_bll:.2f}")
            print(f"Resulting loss rate: {loss_rate:.4f}")

    except ValueError as e:
        print(f"Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
