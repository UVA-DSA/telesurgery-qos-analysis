from abc import ABC

class BaseGEModel(ABC):
    def __init__(self, state_params):
        self.state_params = state_params  # Dict of state-specific params
        self.current_state = 'Good'      # Start in Good state

    def transition_state(self):
        """
        Transition between states based on predefined probabilities.
        """
        raise NotImplementedError("Transition state method not implemented")

    def should_drop(self):
        """
        Process a packet: Determine if it should be dropped or passed.
        """
        raise NotImplementedError("Process packet method not implemented")
    
    def _validate_state_params(self):
        """
        Validate the state parameters.
        """
        raise NotImplementedError("Validate state params method not implemented")
