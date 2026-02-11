from netfi.models import GEClassicModel
from copy import deepcopy

import json
with open('src/netfi/canonical_configs/packet_loss_config.json', 'r') as file:
    state_params = json.load(file)["GE_Classic"]

# Instantiate the model
def simulate_ge(state_params, total_packets=1000, starting_state='Good'):
    # Instantiate the model
    model = GEClassicModel(state_params)
    if starting_state != 'Good':
        model.current_state = starting_state

    # Track statistics
    dropped_packets = 0
    total_bll = 0
    bll_count = 0
    current_bll = 0
    state_counts = {'Good': 0, 'Bad': 0}  # Track time spent in each state

    for packet in range(total_packets):
        # Record current state before processing packet
        state_counts[model.current_state] += 1
        
        current_dropped = model.process_packet()
        
        if current_dropped:
            dropped_packets += 1
            current_bll += 1
            
            # If this is the last packet and it's part of a burst
            if packet == total_packets - 1 and current_bll > 0:
                total_bll += current_bll
                bll_count += 1
        else:
            # If we just finished a burst
            if current_bll > 0:
                total_bll += current_bll
                bll_count += 1
                current_bll = 0

    loss_rate = dropped_packets / total_packets
    avg_bll = total_bll / bll_count if bll_count > 0 else 0
    state_proportions = {
        state: count/total_packets 
        for state, count in state_counts.items()
    }
    
    return loss_rate, avg_bll, state_proportions

# Test 1: No packet loss when h=k=1
no_loss_params = deepcopy(state_params)
no_loss_params['Good']['params']['k'] = 1
no_loss_params['Bad']['params']['h'] = 1
loss_rate, avg_bll, state_props = simulate_ge(no_loss_params)
print("\nTest 1: No packet loss (h=k=1)")
print(f"Packet Loss Rate: {loss_rate:.2%}")
assert abs(loss_rate - 0.0) < 0.01, "Expected loss rate very close to 0% with h=k=1"

# Test 2: Complete packet loss when h=k=0
all_loss_params = deepcopy(state_params)
all_loss_params['Good']['params']['k'] = 0
all_loss_params['Bad']['params']['h'] = 0
loss_rate, avg_bll, state_props = simulate_ge(all_loss_params)
print("\nTest 2: Complete packet loss (h=k=0)")
print(f"Packet Loss Rate: {loss_rate:.2%}")
assert abs(loss_rate - 1.0) < 0.01, "Expected loss rate very close to 100% with h=k=0"

# Test 2.5: Mixed case - Good state never drops (k=1), Bad state always drops (h=0)
mixed_params = deepcopy(state_params)
mixed_params['Good']['params']['k'] = 1  # Never drop in Good state
mixed_params['Bad']['params']['h'] = 0   # Always drop in Bad state

# Calculate theoretical steady state probability for Bad state
q = mixed_params['Good']['transitions']['Bad']  # Good->Bad probability
r = mixed_params['Bad']['transitions']['Good']  # Bad->Good probability
theoretical_bad_prob = q / (q + r)

# Run simulation with enough packets for stable statistics
loss_rate, avg_bll, state_props = simulate_ge(mixed_params, total_packets=1000)
print("\nTest 2.5: Mixed case (k=1, h=0)")
print(f"Theoretical Bad State Probability: {theoretical_bad_prob:.2%}")
print(f"Observed Loss Rate: {loss_rate:.2%}")
print(f"Difference: {abs(theoretical_bad_prob - loss_rate):.2%}")
assert abs(theoretical_bad_prob - loss_rate) < 0.1, "Observed loss rate significantly differs from theoretical probability"


# Test 3: Always stay in Good state
always_good_params = deepcopy(state_params)
always_good_params['Good']['transitions']['Good'] = 1.0
always_good_params['Good']['transitions']['Bad'] = 0.0
loss_rate, avg_bll, state_props = simulate_ge(always_good_params)
print("\nTest 3: Always in Good state")
print(f"Packet Loss Rate: {loss_rate:.2%}")
assert loss_rate < 0.01, "Expected very low loss rate when always in Good state"

# Test 4: Always stay in Bad state
always_bad_params = deepcopy(state_params)
always_bad_params['Bad']['transitions']['Bad'] = 1.0
always_bad_params['Bad']['transitions']['Good'] = 0.0
print(always_bad_params)
loss_rate, avg_bll, state_props = simulate_ge(always_bad_params, starting_state='Bad')
print("\nTest 4: Always in Bad state")
print(f"Packet Loss Rate: {loss_rate:.2%}")
h = always_bad_params['Bad']['params']['h']
expected_loss_rate = 1 - h
assert abs(loss_rate - expected_loss_rate) < 0.01, f"Expected loss rate close to {expected_loss_rate:.2%} when always in Bad state"

# Test 5: Check steady state probabilities
test_params = deepcopy(state_params)
q = test_params['Good']['transitions']['Bad']  # Good->Bad probability
r = test_params['Bad']['transitions']['Good']  # Bad->Good probability
theoretical_bad_prob = q / (q + r)
theoretical_good_prob = r / (q + r)

# Run longer simulation to get better statistics
loss_rate, avg_bll, state_props = simulate_ge(test_params, total_packets=10000)
print("\nTest 5: Steady state probabilities")
print(f"Theoretical state probabilities - Good: {theoretical_good_prob:.2%}, Bad: {theoretical_bad_prob:.2%}")
print(f"Observed state proportions - Good: {state_props['Good']:.2%}, Bad: {state_props['Bad']:.2%}")
print(f"Differences - Good: {abs(theoretical_good_prob - state_props['Good']):.2%}, Bad: {abs(theoretical_bad_prob - state_props['Bad']):.2%}")

# Assert that observed proportions are close to theoretical probabilities
assert abs(theoretical_good_prob - state_props['Good']) < 0.1, "Time in Good state differs significantly from theoretical probability"
assert abs(theoretical_bad_prob - state_props['Bad']) < 0.1, "Time in Bad state differs significantly from theoretical probability"
