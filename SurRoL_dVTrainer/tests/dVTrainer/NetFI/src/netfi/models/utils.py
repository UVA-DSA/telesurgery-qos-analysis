import numpy as np


def pareto_type_ii_sample(alpha, lambda_param, size=1):
    """
    Sample from the Pareto Type II distribution.
    """
    u = np.random.uniform(0, 1, size)  # Uniform random values
    return lambda_param * ((1 - u) ** (-1 / alpha) - 1)