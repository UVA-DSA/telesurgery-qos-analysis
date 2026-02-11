import random
import numpy as np
from netfi.models.ge_base import BaseGEModel

class RandomLossModel(BaseGEModel):
    def __init__(self, state_params):
        """
        Initialize the random loss model.
        
        Args:
            state_params (dict): Dictionary containing state parameters
                Format:
                {
                    'params': {'r': float}  # r is the loss probability (0 to 1)
                }
        """
        super().__init__(state_params)
        self._validate_state_params()
        self.r = self.state_params['params'].get('r', 0.0)  # loss probability

    def _validate_state_params(self):
        """Validate the state parameters."""
        if 'params' not in self.state_params:
            raise ValueError("State parameters must contain 'params' key")
        
        if 'r' not in self.state_params['params']:
            raise ValueError("Parameters must contain loss probability 'r'")
            
        r = self.state_params['params']['r']
        if not (0 <= r <= 1):
            raise ValueError("Loss probability 'r' must be between 0 and 1")

    def transition_state(self):
        """
        No state transitions in random loss model.
        """
        pass  # Random loss model has no state transitions

    def should_drop(self):
        """
        Process a packet: Determine if it should be dropped or passed.
        
        Returns:
            bool: True if packet should be dropped, False otherwise
        """
        return random.random() < self.r
