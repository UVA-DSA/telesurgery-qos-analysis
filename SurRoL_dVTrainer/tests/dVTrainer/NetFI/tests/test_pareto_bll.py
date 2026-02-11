from netfi.models import GEParetoBLLModel
from netfi.parameter_estimation.find_params_for_bll import calculate_required_parameters as calc_params_bll
from netfi.parameter_estimation.find_param_for_lr import calculate_required_parameters as calc_params_lr
from copy import deepcopy
import numpy as np

import json
with open('src/netfi/canonical_configs/packet_loss_config.json', 'r') as file:
    state_params = json.load(file)["GE_Pareto_BLL"]

def simulate_pareto_bll(state_params, total_packets=1000, starting_state='Good'):
    # Instantiate the model
    model = GEParetoBLLModel(state_params)
    if starting_state != 'Good':
        model.current_state = starting_state

    # Track statistics
    dropped_packets = 0
    total_bll = {'Good': 0, 'Bad': 0}
    bll_count = {'Good': 0, 'Bad': 0}
    current_bll = 0
    burst_start_state = None
    state_counts = {'Good': 0, 'Bad': 0, 'Intermediate1': 0, 'Intermediate2': 0}

    for packet in range(total_packets):
        # Record current state before processing packet
        state_counts[model.current_state] += 1
        
        current_dropped = model.process_packet()
        
        if current_dropped:
            dropped_packets += 1
            
            # Start of new burst
            if current_bll == 0:
                burst_start_state = model.current_state
                if burst_start_state in ['Good', 'Bad']:  # Only track Good/Bad bursts
                    current_bll = 1
            else:
                current_bll += 1
            
            # If this is the last packet and it's part of a burst
            if packet == total_packets - 1 and current_bll > 0 and burst_start_state in ['Good', 'Bad']:
                total_bll[burst_start_state] += current_bll
                bll_count[burst_start_state] += 1
        else:
            # If we just finished a burst
            if current_bll > 0 and burst_start_state in ['Good', 'Bad']:
                total_bll[burst_start_state] += current_bll
                bll_count[burst_start_state] += 1
                current_bll = 0
                burst_start_state = None

    loss_rate = dropped_packets / total_packets
    avg_bll = {
        state: total_bll[state] / bll_count[state] if bll_count[state] > 0 else 0
        for state in ['Good', 'Bad']
    }
    state_proportions = {
        state: count/total_packets 
        for state, count in state_counts.items()
    }
    
    return loss_rate, avg_bll, state_proportions

# Test 1: Check steady state probabilities
test_params = deepcopy(state_params)

# Get transition probabilities from each state to others
g_i1 = test_params['Good']['transitions']['Intermediate1']
g_i2 = test_params['Good']['transitions']['Intermediate2'] 
g_b = test_params['Good']['transitions']['Bad']
g_g = test_params['Good']['transitions']['Good']

b_i1 = test_params['Bad']['transitions']['Intermediate1']
b_i2 = test_params['Bad']['transitions']['Intermediate2']
b_g = test_params['Bad']['transitions']['Good']
b_b = test_params['Bad']['transitions']['Bad']

i1_g = test_params['Intermediate1']['transitions']['Good']
i1_b = test_params['Intermediate1']['transitions']['Bad']
i1_i2 = test_params['Intermediate1']['transitions']['Intermediate2']
i1_i1 = test_params['Intermediate1']['transitions']['Intermediate1']

i2_g = test_params['Intermediate2']['transitions']['Good']
i2_b = test_params['Intermediate2']['transitions']['Bad']
i2_i1 = test_params['Intermediate2']['transitions']['Intermediate1']
i2_i2 = test_params['Intermediate2']['transitions']['Intermediate2']

# Calculate theoretical steady state probabilities using transition matrix
P = np.array([
    [g_g, g_b, g_i1, g_i2],
    [b_g, b_b, b_i1, b_i2],
    [i1_g, i1_b, i1_i1, i1_i2],
    [i2_g, i2_b, i2_i1, i2_i2]
])

# Solve for steady state: πP = π where π is the steady state vector
# For a Markov chain, the steady state vector π satisfies πP = π
# This means π is an eigenvector of P^T with eigenvalue 1
# 1. Get eigenvalues and eigenvectors of transposed transition matrix P^T
eigenvals, eigenvecs = np.linalg.eig(P.T)
# 2. Find eigenvector corresponding to eigenvalue closest to 1
steady_state = eigenvecs[:, np.argmin(np.abs(eigenvals - 1))].real
# 3. Normalize the eigenvector so probabilities sum to 1
steady_state = steady_state / steady_state.sum()

theoretical_probs = {
    'Good': steady_state[0],
    'Bad': steady_state[1], 
    'Intermediate1': steady_state[2],
    'Intermediate2': steady_state[3]
}

# Run simulation
loss_rate, avg_bll, state_props = simulate_pareto_bll(test_params, total_packets=10000)
print("\nTest 1: Steady state probabilities")
for state in theoretical_probs:
    print(f"{state} - Theoretical: {theoretical_probs[state]:.2%}, Observed: {state_props[state]:.2%}")
    if abs(theoretical_probs[state] - state_props[state]) < 0.1:
        print(f"\033[92m✓ Time in {state} matches theoretical probability\033[0m")
    else:
        print(f"\033[91m✗ Time in {state} differs significantly from theoretical probability\033[0m")

# Test 2: BLL-based test
bll_test_params = deepcopy(state_params)
# Find lambdas for target BLLs using fixed alpha from config
alpha = state_params['Good']['params']['alpha']  # Use existing alpha
params_good = calc_params_bll(target_avg_bll=5, fixed_alpha=alpha)
params_bad = calc_params_bll(target_avg_bll=12, fixed_alpha=alpha)

# Update parameters
bll_test_params['Good']['params']['lambda'] = params_good['lambda']
bll_test_params['Bad']['params']['lambda'] = params_bad['lambda']

# Make states stay in Good/Bad (no transitions to intermediate states)
bll_test_params['Good']['transitions']['Good'] = 1.0
bll_test_params['Good']['transitions']['Intermediate1'] = 0.0
bll_test_params['Good']['transitions']['Intermediate2'] = 0.0
bll_test_params['Good']['transitions']['Bad'] = 0.0

bll_test_params['Bad']['transitions']['Bad'] = 1.0
bll_test_params['Bad']['transitions']['Intermediate1'] = 0.0
bll_test_params['Bad']['transitions']['Intermediate2'] = 0.0
bll_test_params['Bad']['transitions']['Good'] = 0.0

# Run simulations for both states
_, avg_bll_good, _ = simulate_pareto_bll(bll_test_params, total_packets=10000, starting_state='Good')
_, avg_bll_bad, _ = simulate_pareto_bll(bll_test_params, total_packets=10000, starting_state='Bad')

print("\nTest 2: BLL Test")
print(f"Good state - Target BLL: 5.00, Observed: {avg_bll_good['Good']:.2f}")
print(f"Bad state - Target BLL: 12.00, Observed: {avg_bll_bad['Bad']:.2f}")
if abs(avg_bll_good['Good'] - 5.0) < 1.0:
    print("\033[92m✓ BLL in Good state matches target\033[0m")
else:
    print("\033[91m✗ BLL in Good state differs significantly from target\033[0m")
if abs(avg_bll_bad['Bad'] - 12.0) < 1.0:
    print("\033[92m✓ BLL in Bad state matches target\033[0m")
else:
    print("\033[91m✗ BLL in Bad state differs significantly from target\033[0m")

# Test 3: Loss Rate-based test
lr_test_params = deepcopy(state_params)
# Find lambdas for target loss rates using fixed alpha
params_good_lr = calc_params_lr(target_loss_rate=0.05, fixed_alpha=alpha)
params_bad_lr = calc_params_lr(target_loss_rate=0.20, fixed_alpha=alpha)

# Update parameters
lr_test_params['Good']['params']['lambda'] = params_good_lr['lambda']
lr_test_params['Bad']['params']['lambda'] = params_bad_lr['lambda']

# Make states stay in Good/Bad
lr_test_params['Good']['transitions']['Good'] = 1.0
lr_test_params['Good']['transitions']['Intermediate1'] = 0.0
lr_test_params['Good']['transitions']['Intermediate2'] = 0.0
lr_test_params['Good']['transitions']['Bad'] = 0.0

lr_test_params['Bad']['transitions']['Bad'] = 1.0
lr_test_params['Bad']['transitions']['Intermediate1'] = 0.0
lr_test_params['Bad']['transitions']['Intermediate2'] = 0.0
lr_test_params['Bad']['transitions']['Good'] = 0.0

# Run simulations for both states
loss_rate_good, _, _ = simulate_pareto_bll(lr_test_params, total_packets=10000, starting_state='Good')
loss_rate_bad, _, _ = simulate_pareto_bll(lr_test_params, total_packets=10000, starting_state='Bad')

print("\nTest 3: Loss Rate Test")
print(f"Good state - Target LR: 5.00%, Observed: {loss_rate_good:.2%}")
print(f"Bad state - Target LR: 20.00%, Observed: {loss_rate_bad:.2%}")
if abs(loss_rate_good - 0.05) < 0.01:
    print("\033[92m✓ Loss rate in Good state matches target\033[0m")
else:
    print("\033[91m✗ Loss rate in Good state differs significantly from target\033[0m")
if abs(loss_rate_bad - 0.20) < 0.01:
    print("\033[92m✓ Loss rate in Bad state matches target\033[0m")
else:
    print("\033[91m✗ Loss rate in Bad state differs significantly from target\033[0m")
