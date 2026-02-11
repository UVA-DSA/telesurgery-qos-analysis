import random
import numpy as np

from netfi.models.ge_base import BaseGEModel

class GEClassicModel(BaseGEModel):
    def __init__(self, state_params):
        """
        Initialize the two-state Gilbert-Elliott model.
        
        Args:
            state_params (dict): Dictionary containing state parameters
                Format:
                {
                    'Good': {'transitions': {'Good': p, 'Bad': q}, 'params': {'k': k}},
                    'Bad': {'transitions': {'Good': r, 'Bad': s}, 'params': {'h': h}}
                }
        """
        super().__init__(state_params)
        self._validate_state_params()
        self.k = self.state_params['Good']['params'].get('k', 1.0) # correct transmission rate in good state
        self.h = self.state_params['Bad']['params'].get('h', 1.0)  # correct transmission rate in bad state
        self.current_state = 'Good'  # Start in good state

    def _validate_state_params(self):
        if 'h' in self.state_params['Bad']['params']:
            assert 0 <= self.state_params['Bad']['params']['h'] <= 1, "h must be between 0 and 1"

        if 'k' in self.state_params['Good']['params']:
            assert 0 <= self.state_params['Good']['params']['k'] <= 1, "k must be between 0 and 1"

        for state in self.state_params:
            if state not in ['Good', 'Bad']:
                raise ValueError(f"Invalid state: {state}")
        if not np.isclose(self.state_params['Good']['transitions']['Good'] + self.state_params['Good']['transitions']['Bad'], 1.0):
            raise ValueError("Good state transitions must sum to 1")
        if not np.isclose(self.state_params['Bad']['transitions']['Good'] + self.state_params['Bad']['transitions']['Bad'], 1.0):
            raise ValueError("Bad state transitions must sum to 1")

    def transition_state(self):
        """
        Transition between states based on predefined probabilities.
        """
        transition_probs = self.state_params[self.current_state]['transitions']
        self.current_state = random.choices(
            list(transition_probs.keys()), 
            weights=list(transition_probs.values())
        )[0]

    def should_drop(self):
        """
        Process a packet: Determine if it should be dropped or passed.
        Returns:
            bool: True if packet should be dropped, False otherwise
        """
        self.transition_state()

        if self.current_state == 'Good':
            return random.random() < (1 - self.k)
        
        # In bad state, drop packet with probability h
        return random.random() < (1 - self.h)
