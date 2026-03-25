"""
ALGOL 26 Built-in Functions

Provides built-in operations like println, math functions, etc.
"""

import math
from typing import Any, List

# Import distribution classes (define in separate module)
from src.distributions import Bernoulli, Normal, Uniform, Distribution, Conditional, Categorical


class Builtins:
    """Namespace for built-in functions."""

    @staticmethod
    def println(*args):
        """Print arguments with spaces, followed by newline."""
        # Convert each arg to string, handling arrays/records simply
        parts = []
        for arg in args:
            if isinstance(arg, list):
                # Simple array formatting
                parts.append('[' + ', '.join(str(x) for x in arg) + ']')
            elif isinstance(arg, dict):
                # Simple record formatting
                fields = ', '.join(f"{k}: {v}" for k, v in arg.items())
                parts.append('{' + fields + '}')
            else:
                parts.append(str(arg))
        print(' '.join(parts))

    @staticmethod
    def print(*args):
        """Print without newline."""
        parts = []
        for arg in args:
            if isinstance(arg, list):
                parts.append('[' + ', '.join(str(x) for x in arg) + ']')
            elif isinstance(arg, dict):
                fields = ', '.join(f"{k}: {v}" for k, v in arg.items())
                parts.append('{' + fields + '}')
            else:
                parts.append(str(arg))
        print(' '.join(parts), end='')

    @staticmethod
    def sqrt(x: float) -> float:
        return math.sqrt(x)

    @staticmethod
    def sin(x: float) -> float:
        return math.sin(x)

    @staticmethod
    def cos(x: float) -> float:
        return math.cos(x)

    @staticmethod
    def tan(x: float) -> float:
        return math.tan(x)

    @staticmethod
    def exp(x: float) -> float:
        return math.exp(x)

    @staticmethod
    def log(x: float) -> float:
        return math.log(x)

    @staticmethod
    def log10(x: float) -> float:
        return math.log10(x)

    @staticmethod
    def abs(x: Union[int, float]) -> Union[int, float]:
        return abs(x)

    @staticmethod
    def floor(x: float) -> int:
        return math.floor(x)

    @staticmethod
    def ceil(x: float) -> int:
        return math.ceil(x)

    @staticmethod
    def round(x: float, ndigits: int = 0) -> float:
        return round(x, ndigits)

    @staticmethod
    def max(*args) -> Any:
        return max(args)

    @staticmethod
    def min(*args) -> Any:
        return min(args)

    @staticmethod
    def sum(args: List[Any]) -> Any:
        return sum(args)

    @staticmethod
    def len(x: Union[str, list, dict]) -> int:
        return len(x)

    # Probabilistic programming: distribution constructors
    @staticmethod
    def bernoulli(p: float) -> Distribution:
        """Construct Bernoulli(p) distribution."""
        return Bernoulli(p)

    @staticmethod
    def normal(mean: float, stddev: float) -> Distribution:
        """Construct Normal(mean, stddev) distribution."""
        return Normal(mean, stddev)

    @staticmethod
    def uniform(a: Any, b: Any) -> Distribution:
        """Construct Uniform(a, b) distribution (int or float)."""
        return Uniform(a, b)

    # Probabilistic programming stub
    @staticmethod
    def sample(distribution):
        """Sample from a distribution. MVP stub returns deterministic value."""
        # In real implementation, this would sample from Distribution object
        # For MVP, if distribution is a number, return it; if object with .sample(), call it; else 0
        if hasattr(distribution, 'sample'):
            return distribution.sample()
        # Stub: for Distribution<T>, return a fixed value (0 or mean)
        # Try to infer a sensible default
        if isinstance(distribution, (int, float)):
            return distribution
        return 0

    @staticmethod
    def infer(dist):
        """
        Perform exact inference on a conditional distribution if possible.
        If `dist` is a Conditional and its base distribution has finite discrete support,
        returns a Categorical distribution representing the exact posterior.
        Otherwise, returns the original distribution (possibly with a warning).
        """
        if not isinstance(dist, Conditional):
            # Not a conditional, cannot infer
            return dist
        base = dist.base_dist
        # Check if base has get_support and pmf methods
        if not (hasattr(base, 'get_support') and hasattr(base, 'pmf')):
            return dist
        try:
            support = base.get_support()
        except NotImplementedError:
            return dist
        # Compute unnormalized posterior
        total = 0.0
        probs = {}
        for value in support:
            try:
                p_prior = base.pmf(value)
            except (NotImplementedError, TypeError):
                p_prior = 0
            if p_prior <= 0:
                continue
            if dist.condition(value):
                probs[value] = p_prior
                total += p_prior
        if total == 0:
            raise ValueError("Condition has zero probability under the prior distribution")
        # Normalize
        for value in probs:
            probs[value] /= total
        return Categorical(probs)

    # Conversion functions
    @staticmethod
    def int(x) -> int:
        if isinstance(x, (int, float)):
            return int(x)
        if isinstance(x, str):
            return int(x)
        raise TypeError(f"Cannot convert {type(x)} to int")

    @staticmethod
    def real(x) -> float:
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            return float(x)
        raise TypeError(f"Cannot convert {type(x)} to real")

    @staticmethod
    def char(x) -> str:
        if isinstance(x, int):
            return chr(x)
        if isinstance(x, str) and len(x) == 1:
            return x
        raise TypeError(f"Cannot convert {type(x)} to char")

    @staticmethod
    def string(x) -> str:
        return str(x)

    @staticmethod
    def bytes(x) -> bytes:
        if isinstance(x, str):
            return x.encode('utf-8')
        if isinstance(x, bytes):
            return x
        raise TypeError(f"Cannot convert {type(x)} to bytes")


# Helper for type checking
def is_number(x):
    return isinstance(x, (int, float))

def is_integer(x):
    return isinstance(x, int)

def is_real(x):
    return isinstance(x, float)

def is_boolean(x):
    return isinstance(x, bool)

def is_string(x):
    return isinstance(x, str)

def is_char(x):
    return isinstance(x, str) and len(x) == 1

def is_array(x):
    return isinstance(x, list)

def is_record(x):
    return isinstance(x, dict)
