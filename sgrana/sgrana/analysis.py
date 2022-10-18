import numpy as np
import torch
import ddks
from tqdm.auto import tqdm


def rdks(P, T):
    try:
        ddks_dist = ddks.methods.rdKS(orthant_method="ranksort")
    except:
        print("Warning: not using ranksort method")
        ddks_dist = ddks.methods.rdKS()

    return ddks_dist(P, T)


def bootstrap(P, T, m=None, n_trials=10, poisson=False, use_tqdm=True):
    """Perform bootstrap sampling estimation of the rdKS value between P and T.

    Resamples P and T separately.

    m: the number of points to include in the resampled dataset. By default,
        this is None, so resampled datasets are the same size as the original
        datasets. Since the resampling is done with replacement, m may
        be larger than the number of points in the dataset; the resulting
        resamplings will just have some duplicate points.

    poisson: use Poisson resampling instead of actually selecting elements from
        a list.  It is not guaranteed that the resampled datasets will have size
        _exactly_ equal to m (or the original dataset size), but will be close.
        Can be faster for large datasets.
    """

    rng = np.random.default_rng()

    def _resample(X):
        indices = rng.choice(X.shape[0], size=(m if m else X.shape[0],), replace=True)
        return X[indices]

    def _poisson_resample(X):
        counts = rng.poisson(lam=m / X.shape[0] if m else 1.0, size=(X.shape[0]))
        X_resampled = torch.zeros((counts.sum(), 3))

        j = 0
        for i in range(X.shape[0]):
            X_resampled[j : j + counts[i], :] = X[i]
            j += counts[i]

        return X_resampled

    resample = _poisson_resample if poisson else _resample

    try:
        ddks_dist = ddks.methods.rdKS(orthant_method="ranksort")
    except:
        print("Warning: not using ranksort method")
        ddks_dist = ddks.methods.rdKS()

    distances = np.zeros((n_trials,))

    iterator = range(n_trials)
    if use_tqdm:
        iterator = tqdm(iterator)

    for i in iterator:
        _P = resample(P)
        _T = resample(T)
        distances[i] = ddks_dist(_P, _T).item()

    return distances
