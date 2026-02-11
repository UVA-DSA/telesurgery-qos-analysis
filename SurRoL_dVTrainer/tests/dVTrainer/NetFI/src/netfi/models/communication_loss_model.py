import random
import time
from typing import Dict

class CommunicationLossModel:
    """
    A packet loss model that creates bursts of packet loss with uniform length distribution.
    
    The model works as follows:
    1. There is a fixed probability of entering a loss period
    2. Once in a loss period, the length is uniformly sampled between min_loss_length and max_loss_length
    3. During a loss period, all packets are dropped
    4. After a loss period, there is a cooldown period during which no new loss periods can start
    
    The model supports two units for loss and cooldown periods:
    - 'packet': Lengths are measured in number of packets
    - 'milliseconds': Lengths are measured in time (milliseconds)
    """
    
    def __init__(self, 
                 params: Dict = None):
        """
        Initialize the Communication Loss Model.
        
        Args:
            params: Dictionary containing model parameters with keys:
                - loss_prob: Probability of entering a loss period (0.0-1.0)
                - min_loss_length: Minimum length of a loss period
                - max_loss_length: Maximum length of a loss period
                - cooldown_period: Period to wait after a loss period before another can start
                - unit: Either 'packet' or 'milliseconds' (default: 'packet')
        """
        if params is None:
            params = {}
            
        self.loss_prob = params.get('loss_prob', 0.01)
        self.min_loss_length = params.get('min_loss_length', 1)
        self.max_loss_length = params.get('max_loss_length', 5)
        self.cooldown_period = params.get('cooldown_period', 10)
        self.unit = params.get('unit', 'packet')
        
        if self.unit not in ['packet', 'milliseconds']:
            raise ValueError("Unit must be either 'packet' or 'milliseconds'")
        
        # Internal state
        self.in_loss_period = False
        self.remaining_loss = 0
        self.cooldown_counter = 0
        self.last_packet_time = time.time() * 1000  # Current time in milliseconds
        self.loss_start_time = 0
        self.cooldown_start_time = 0
    
    def reset(self):
        """Reset the model state."""
        self.in_loss_period = False
        self.remaining_loss = 0
        self.cooldown_counter = 0
        self.last_packet_time = time.time() * 1000
        self.loss_start_time = 0
        self.cooldown_start_time = 0
    
    def _update_time(self):
        """Update the current time and handle time-based state transitions."""
        current_time = time.time() * 1000  # Current time in milliseconds
        
        if self.unit == 'milliseconds':
            # Handle loss period
            if self.in_loss_period:
                elapsed = current_time - self.loss_start_time
                if elapsed >= self.remaining_loss:
                    self.in_loss_period = False
                    self.cooldown_start_time = current_time
            
            # Handle cooldown period
            elif self.cooldown_start_time > 0:
                elapsed = current_time - self.cooldown_start_time
                if elapsed >= self.cooldown_period:
                    self.cooldown_start_time = 0
        
        self.last_packet_time = current_time
    
    def should_drop(self) -> bool:
        """
        Determine if a packet should be dropped.
        
        Returns:
            True if the packet should be dropped, False otherwise
        """
        self._update_time()
        
        # If we're in a loss period
        if self.in_loss_period:
            if self.unit == 'packet':
                self.remaining_loss -= 1
                if self.remaining_loss <= 0:
                    self.in_loss_period = False
                    self.cooldown_counter = self.cooldown_period
            return True
        
        # If we're in cooldown
        if self.unit == 'packet':
            if self.cooldown_counter > 0:
                self.cooldown_counter -= 1
                return False
        elif self.cooldown_start_time > 0:
            return False
        
        # Randomly decide if we should enter a loss period
        if random.random() < self.loss_prob:
            self.in_loss_period = True
            
            if self.unit == 'packet':
                self.remaining_loss = random.randint(self.min_loss_length, self.max_loss_length)
                if self.remaining_loss <= 1:
                    self.in_loss_period = False
                    self.cooldown_counter = self.cooldown_period
                else:
                    self.remaining_loss -= 1
            else:  # milliseconds
                self.remaining_loss = random.randint(self.min_loss_length, self.max_loss_length)
                self.loss_start_time = self.last_packet_time
            
            return True
        
        return False
