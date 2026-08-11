"""SinhArcsinh distribution math for fantabeto (replaces tensorflow-probability).

Parametrization follows the project README's reference pdf:
    mu = loc, sigma = scale, eps = skewness, delta = tailweight.

The SAME definition is used for the training loss (TF) and for sampling
(numpy), so notebooks 6 and 7 stay self-consistent.
"""
import numpy as np
import tensorflow as tf
from scipy.stats import norm

_ARCSINH2 = np.arcsinh(2.0)


def _mul_np(delta):
    return 2.0 / np.sinh(_ARCSINH2 * delta)


def sinharcsinh_pdf_np(x, mu, sigma, eps, delta):
    """Reference pdf (README formula)."""
    x = np.asarray(x, dtype=np.float64)
    mul = _mul_np(delta)
    z = (x - mu) / (sigma * mul)
    S = np.sinh(-eps + (1.0 / delta) * np.arcsinh(z))
    return (np.exp(-0.5 * S * S) * np.sqrt(1.0 + S * S)
            / (sigma * mul * delta)
            / np.sqrt(1.0 + z * z)
            / np.sqrt(2.0 * np.pi))


def constrain_params_np(loc, raw_scale, skewness, raw_tail,
                        tail_min=0.5, tail_range=1.2):
    """Apply the same constraints the network output uses (numpy)."""
    sigma = 1e-3 + np.logaddexp(0.0, raw_scale)          # softplus
    delta = tail_min + tail_range * (1.0 / (1.0 + np.exp(-raw_tail)))  # sigmoid
    return float(loc), float(sigma), float(skewness), float(delta)


def sinharcsinh_nll_tf(y_true, params, tail_min=0.5, tail_range=1.2):
    """Mean negative log-likelihood under SinhArcsinh.

    params: (batch, 4) raw outputs [loc, raw_scale, skewness, raw_tail].
    y_true: (batch, 1) or (batch,) observed values.
    """
    y = tf.reshape(tf.cast(y_true, tf.float32), (-1,))
    loc = params[..., 0]
    sigma = 1e-3 + tf.math.softplus(params[..., 1])
    eps = params[..., 2]
    delta = tail_min + tail_range * tf.math.sigmoid(params[..., 3])

    mul = 2.0 / tf.math.sinh(tf.constant(_ARCSINH2, tf.float32) * delta)
    z = (y - loc) / (sigma * mul)
    S = tf.math.sinh(-eps + (1.0 / delta) * tf.math.asinh(z))
    log_pdf = (-0.5 * S * S
               + 0.5 * tf.math.log(1.0 + S * S)
               - tf.math.log(sigma * mul * delta)
               - 0.5 * tf.math.log(1.0 + z * z)
               - 0.5 * tf.math.log(2.0 * np.pi))
    return -tf.reduce_mean(log_pdf)


def sample_sinharcsinh_np(mu, sigma, eps, delta, size):
    """Closed-form inverse-transform sampler.

    If S ~ N(0,1), then x = mu + sigma*mul*sinh(delta*(arcsinh(S)+eps)).
    """
    rng = np.random.default_rng()
    S = rng.standard_normal(size)
    mul = _mul_np(delta)
    z = np.sinh(delta * (np.arcsinh(S) + eps))
    return mu + sigma * mul * z


def sinharcsinh_quantile_np(q, mu, sigma, eps, delta):
    """Inverse CDF (quantile) of the SinhArcsinh distribution.

    Same monotone transform as the sampler, evaluated at S = Phi^{-1}(q).
    q may be a scalar or array in (0, 1).
    """
    S = norm.ppf(q)
    mul = _mul_np(delta)
    z = np.sinh(delta * (np.arcsinh(S) + eps))
    return mu + sigma * mul * z


def sample_bernoulli_np(p, size):
    rng = np.random.default_rng()
    return (rng.random(size) < p).astype(int)
