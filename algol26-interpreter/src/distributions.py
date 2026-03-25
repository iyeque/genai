"""
Probabilistic Programming: Distribution Types and Operations

Provides runtime representation of distributions and sampling primitives.
Supports:
- Discrete: Bernoulli, Uniform (int)
- Continuous (stub): Normal, Uniform (float)
- Conditioning via rejection sampling (MVP)
- Exact inference via enumeration for finite discrete distributions
"""

import random
import math
from typing import Any, Callable, Optional, List, Dict, Iterable


class Distribution:
    """Base class for all distributions."""
    def sample(self) -> Any:
        raise NotImplementedError()

    def get_support(self) -> Iterable[Any]:
        """Return an iterable of all possible values (for finite discrete distributions)."""
        raise NotImplementedError("This distribution does not have a finite support enumeration")

    def pmf(self, value: Any) -> float:
        """Return the probability mass for a given value (for discrete distributions)."""
        raise NotImplementedError("PMF not defined for this distribution")

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class Bernoulli(Distribution):
    """Bernoulli(p) returns True with probability p, False otherwise."""
    def __init__(self, p: float):
        if not 0 <= p <= 1:
            raise ValueError(f"Bernoulli probability must be in [0,1], got {p}")
        self.p = p

    def sample(self) -> bool:
        return random.random() < self.p

    def get_support(self) -> List[bool]:
        return [True, False]

    def pmf(self, value: bool) -> float:
        return self.p if value else 1.0 - self.p

    def __repr__(self):
        return f"Bernoulli(p={self.p})"


class Normal(Distribution):
    """Normal(mean, stddev) using Box-Muller transform."""
    def __init__(self, mean: float, stddev: float):
        if stddev <= 0:
            raise ValueError(f"Normal stddev must be positive, got {stddev}")
        self.mean = mean
        self.stddev = stddev
        self._has_next = False
        self._next = 0.0

    def sample(self) -> float:
        # Box-Muller transform for two independent samples
        if not self._has_next:
            u1 = random.random()
            u2 = random.random()
            while u1 <= 0:
                u1 = random.random()
            z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
            self._next = math.sqrt(-2.0 * math.log(u1)) * math.sin(2.0 * math.pi * u2)
            self._has_next = True
        else:
            z = self._next
            self._has_next = False
        return self.mean + z * self.stddev

    def __repr__(self):
        return f"Normal(μ={self.mean}, σ={self.stddev})"


class Uniform(Distribution):
    """Uniform(a, b) returns values in [a, b) for ints? For floats: [a, b) typical."""
    def __init__(self, a: Any, b: Any):
        if isinstance(a, int) and isinstance(b, int):
            self.discrete = True
            self.low = int(a)
            self.high = int(b)
            if self.low >= self.high:
                raise ValueError(f"Uniform integer range invalid: [{self.low}, {self.high})")
        else:
            # Treat as float domain
            self.discrete = False
            self.low = float(a)
            self.high = float(b)
            if self.low >= self.high:
                raise ValueError(f"Uniform float range invalid: [{self.low}, {self.high})")

    def sample(self) -> Any:
        if self.discrete:
            return random.randint(self.low, self.high - 1)
        else:
            return random.uniform(self.low, self.high)

    def get_support(self) -> List[int]:
        if not self.discrete:
            raise NotImplementedError("Continuous uniform does not have finite support")
        return list(range(self.low, self.high))

    def pmf(self, value: int) -> float:
        if not self.discrete:
            raise NotImplementedError("PMF not defined for continuous uniform")
        if self.low <= value < self.high:
            return 1.0 / (self.high - self.low)
        else:
            return 0.0

    def __repr__(self):
        if self.discrete:
            return f"UniformInt([{self.low}, {self.high}))"
        else:
            return f"UniformFloat([{self.low}, {self.high}))"


class Conditional(Distribution):
    """Conditional distribution: dist given condition.
    Implements rejection sampling for MVP inference.
    """
    def __init__(self, base_dist: Distribution, condition_fn: Callable[[Any], bool], max_attempts: int = 1000):
        self.base_dist = base_dist
        self.condition = condition_fn
        self.max_attempts = max_attempts

    def sample(self) -> Any:
        for _ in range(self.max_attempts):
            candidate = self.base_dist.sample()
            if self.condition(candidate):
                return candidate
        raise RuntimeError(f"Conditional sampling failed after {self.max_attempts} attempts (condition too restrictive)")

    def __repr__(self):
        return f"Conditional({self.base_dist} | condition)"


class Categorical(Distribution):
    """Discrete distribution over a finite set of values with given probabilities."""
    def __init__(self, prob_dict: Dict[Any, float]):
        """
        prob_dict: dict mapping value -> probability (should sum to 1).
        """
        total = sum(prob_dict.values())
        if abs(total - 1.0) > 1e-10:
            raise ValueError(f"Probabilities must sum to 1, got {total}")
        self.values = list(prob_dict.keys())
        self.probs = [prob_dict[v] for v in self.values]
        # Precompute cumulative distribution for efficient sampling
        self.cumdist = []
        cum = 0.0
        for p in self.probs:
            cum += p
            self.cumdist.append(cum)
        # Ensure last is exactly 1
        self.cumdist[-1] = 1.0

    def sample(self) -> Any:
        r = random.random()
        # binary search could be used, but for small support linear is fine
        for i, cum in enumerate(self.cumdist):
            if r < cum:
                return self.values[i]
        return self.values[-1]  # fallback

    def __repr__(self):
        return f"Categorical({dict(zip(self.values, self.probs))})"


def enumerate_distribution(dist: Distribution, num_samples: int = 1000) -> dict:
    """Approximate a distribution by sampling. Returns dict of value -> frequency."""
    counts = {}
    for _ in range(num_samples):
        val = dist.sample()
        counts[val] = counts.get(val, 0) + 1
    return {val: count/num_samples for val, count in counts.items()}


def expectation(dist: Distribution, fn: Optional[Callable[[Any], float]] = None, num_samples: int = 10000) -> float:
    """Compute expectation E[f(X)] by Monte Carlo integration."""
    if fn is None:
        fn = lambda x: x
    total = 0.0
    for _ in range(num_samples):
        x = dist.sample()
        total += fn(x)
    return total / num_samples
