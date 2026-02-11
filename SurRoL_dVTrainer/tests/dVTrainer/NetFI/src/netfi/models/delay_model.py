import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import expon

class DelayModel:
    """
    A class to model network delays using a hyperexponential distribution.
    
    Parameters:
        lower_bound (float): The minimum delay (in ms) added to every sample
        weights (list of float): Probabilities for each exponential component (should sum to 1)
        lambdas (list of float): Rate parameters (λ) for each exponential component
    """
    
    def __init__(self, lower_bound, weights, lambdas):
        self.lower_bound = lower_bound
        self.weights = weights
        self.lambdas = lambdas
        
        # Validate inputs
        if len(weights) != len(lambdas):
            raise ValueError("weights and lambdas must have the same length")
        if not np.isclose(sum(weights), 1.0):
            raise ValueError("weights must sum to 1")
        if any(w < 0 for w in weights) or any(l <= 0 for l in lambdas):
            raise ValueError("weights must be non-negative and lambdas must be positive")

    def sample_delay(self):
        """
        Generate a single delay sample from the hyperexponential distribution.
        
        Returns:
            float: A single delay sample (in ms)
        """
        component = np.random.choice(len(self.weights), p=self.weights)
        sample = np.random.exponential(scale=1.0 / self.lambdas[component])
        return self.lower_bound + sample

    def sample_delays(self, n_samples):
        """
        Generate multiple delay samples.
        
        Parameters:
            n_samples (int): Number of samples to generate
            
        Returns:
            np.array: Array of generated delay samples
        """
        return np.array([self.sample_delay() for _ in range(n_samples)])

    def pdf(self, x):
        """
        Compute the PDF of the hyperexponential distribution.
        
        Parameters:
            x (np.array): Points at which to evaluate the PDF
            
        Returns:
            np.array: The computed PDF values
        """
        pdf_vals = np.zeros_like(x)
        idx = x >= self.lower_bound
        x_shifted = x[idx] - self.lower_bound
        pdf_vals[idx] = sum(w * lamb * np.exp(-lamb * x_shifted) 
                           for w, lamb in zip(self.weights, self.lambdas))
        return pdf_vals

    def plot_distribution(self, n_samples=100000, bins=100):
        """
        Plot histogram of empirical delays and overlay the theoretical PDF.
        
        Parameters:
            n_samples (int): Number of samples to generate for the plot
            bins (int): Number of bins for histogram
        """
        delays = self.sample_delays(n_samples)
        
        plt.figure(figsize=(8, 5))
        plt.hist(delays, bins=bins, density=True, alpha=0.6, color='skyblue',
                edgecolor='black', label='Empirical')
        
        x = np.linspace(self.lower_bound, min(300, np.max(delays)), 1000)
        pdf_vals = self.pdf(x)
        
        plt.plot(x, pdf_vals, 'r-', lw=2, label='Theoretical PDF')
        plt.xlabel('Delay (ms)', fontsize=20)
        plt.ylabel('Probability Density', fontsize=20)
        # plt.title(f'Network Delay Distribution (n = {n_samples:,})')
        plt.legend(fontsize=20)
        plt.grid(True)
        plt.xlim(0, 120)
        plt.xticks(fontsize=16)
        plt.yticks(fontsize=16)
        plt.show()

if __name__ == '__main__':
    np.random.seed(42)  # For reproducibility
    
    # Create 4G delay model
    model_4g = DelayModel(
        lower_bound=15,      # in ms
        weights=[0.8, 0.2],
        lambdas=[1.0/10, 1.0/150]  # Rate parameters in ms^-1
    )
    
    # Create 5G delay model
    model_5g = DelayModel(
        lower_bound=7.5,     # in ms
        weights=[0.8, 0.2],
        lambdas=[1.0/5, 1.0/50]   # Rate parameters in ms^-1
    )
    
    print("Simulating 4G network delay...")
    model_4g.plot_distribution()
    
    print("Simulating 5G network delay...")
    model_5g.plot_distribution()
