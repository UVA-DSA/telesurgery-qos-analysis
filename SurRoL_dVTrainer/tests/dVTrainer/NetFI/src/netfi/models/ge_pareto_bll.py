import numpy as np
import random
from scipy.stats import expon
from scipy.optimize import minimize_scalar

from netfi.models.utils import pareto_type_ii_sample
from netfi.models.ge_base import BaseGEModel


class GEParetoBLLModel(BaseGEModel):
    def __init__(self, state_params):
        super().__init__(state_params)
        #self._validate_state_params()
        self.bll = None

    def _validate_state_params(self):
        # Check that transitions sum to 1 for each state
        valid_states = ['Good', 'Bad', 'Intermediate1', 'Intermediate2']
        for state in self.state_params:
            if state not in valid_states:
                raise ValueError(f"Invalid state: {state}")
            
            transitions = self.state_params[state]['transitions']
            transition_sum = sum(transitions.values())
            if not np.isclose(transition_sum, 1.0):
                raise ValueError(f"Transitions for state {state} must sum to 1, got {transition_sum}")
        # Check that distribution and required parameters are present for each state
        for state, params in self.state_params.items():
            if 'distribution' not in params:
                raise ValueError(f"Distribution type must be specified for state {state}")
            
            dist = params['distribution']
            if dist not in ['pareto', 'exponential']:
                raise ValueError(f"Invalid distribution type '{dist}' for state {state}. Must be 'pareto' or 'exponential'")
            
            if 'params' not in params:
                raise ValueError(f"Parameters must be specified for state {state}")

            if dist == 'pareto':
                if 'alpha' not in params['params']:
                    raise ValueError(f"Alpha parameter required for Pareto distribution in state {state}")
                if 'lambda' not in params['params']:
                    raise ValueError(f"Lambda parameter required for Pareto distribution in state {state}")
            elif dist == 'exponential':
                if 'mu' not in params['params']:
                    raise ValueError(f"Mu parameter required for exponential distribution in state {state}")

    def transition_state(self):
        """
        Transition between states based on predefined probabilities.
        """
        transition_probs = self.state_params[self.current_state]['transitions']
        self.current_state = random.choices(
            list(transition_probs.keys()), 
            weights=list(transition_probs.values())
        )[0]

    def sample_bll(self):
        """
        Sample Burst Loss Length (BLL) for the current state.
        """
        dist = self.state_params[self.current_state]['distribution']
        params = self.state_params[self.current_state]['params']

        if dist == 'pareto':
            # Use the Pareto Type II distribution for sampling
            return int(pareto_type_ii_sample(params['alpha'], params['lambda'], size=1)[0])
        elif dist == 'exponential':
            # Use the exponential distribution for sampling
            return int(expon.rvs(scale=params['mu']))
        else:
            raise ValueError("Unsupported distribution type.")

    def should_drop(self):
        """
        Process a packet: Determine if it should be dropped or passed.
        :param bll: Burst Loss Length to process
        """
        self.transition_state()
        if self.bll is None:
            self.bll = self.sample_bll()

        if self.bll > 0:
            self.bll -= 1
            return True
        else:
            self.bll = None
            return False
