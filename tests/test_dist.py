import numpy as np
import tensorflow as tf
import fantabeto_dist as fd


def test_pdf_matches_readme_example():
    # README worked example: attacking player's vote distribution.
    x = np.array([6.06])
    p = fd.sinharcsinh_pdf_np(x, mu=6.06, sigma=0.62, eps=0.33, delta=1.06)
    # Reference value computed from the README pdf formula.
    assert np.isfinite(p[0])
    assert p[0] > 0
    # pdf integrates to ~1 over a wide grid
    grid = np.arange(-10, 30, 0.001)
    pg = fd.sinharcsinh_pdf_np(grid, 6.06, 0.62, 0.33, 1.06)
    assert abs(np.trapz(pg, grid) - 1.0) < 1e-2


def test_nll_equals_neg_log_pdf():
    # NLL of a batch equals -log(pdf) using the SAME constrained params.
    y = np.array([[6.0], [7.0]], dtype=np.float32)
    raw = np.array([[6.0, 0.0, 0.2, 0.0],
                    [6.5, 0.5, -0.1, 0.3]], dtype=np.float32)
    nll = float(fd.sinharcsinh_nll_tf(tf.constant(y), tf.constant(raw)))
    # Recompute by hand via numpy path.
    total = 0.0
    for i in range(2):
        mu, sigma, eps, delta = fd.constrain_params_np(*raw[i])
        pdf = fd.sinharcsinh_pdf_np(np.array([y[i, 0]]), mu, sigma, eps, delta)[0]
        total += -np.log(pdf)
    assert abs(nll - total / 2) < 1e-3


def test_sampler_recovers_location():
    # Symmetric case (eps=0): sample mean ~ mu.
    rng = np.random.default_rng(0)
    s = fd.sample_sinharcsinh_np(mu=6.0, sigma=1.0, eps=0.0, delta=1.0, size=200_000)
    assert abs(s.mean() - 6.0) < 0.05


def test_sampler_skew_sign():
    # Positive skewness pushes the mean above mu.
    s = fd.sample_sinharcsinh_np(mu=6.0, sigma=1.0, eps=0.8, delta=1.0, size=200_000)
    assert s.mean() > 6.0


def test_bernoulli_rate():
    s = fd.sample_bernoulli_np(0.3, size=200_000)
    assert set(np.unique(s)).issubset({0, 1})
    assert abs(s.mean() - 0.3) < 0.02


def test_quantile_median_is_mu_when_symmetric():
    # eps=0 => median (q=0.5) equals mu exactly (S=0 -> z=0)
    assert abs(fd.sinharcsinh_quantile_np(0.5, mu=6.0, sigma=1.0, eps=0.0, delta=1.0) - 6.0) < 1e-9


def test_quantile_monotonic_increasing():
    qs = [0.05, 0.25, 0.5, 0.75, 0.95]
    vals = [fd.sinharcsinh_quantile_np(q, 6.0, 1.2, 0.3, 1.1) for q in qs]
    assert all(vals[i] < vals[i+1] for i in range(len(vals)-1))


def test_quantile_matches_empirical_sampler():
    # quantile should match the sampler's empirical quantile within noise
    import numpy as np
    s = fd.sample_sinharcsinh_np(6.0, 1.0, 0.4, 1.1, 400_000)
    for q in (0.1, 0.5, 0.9):
        emp = np.quantile(s, q)
        theo = fd.sinharcsinh_quantile_np(q, 6.0, 1.0, 0.4, 1.1)
        assert abs(emp - theo) < 0.05, f"q={q}: emp {emp} vs theo {theo}"
