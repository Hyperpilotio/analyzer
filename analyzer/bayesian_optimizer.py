from __future__ import print_function
from __future__ import division

import numpy as np
import logging
log = logging.getLogger(__name__)
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern
from scipy.stats import norm
from scipy.optimize import minimize

log.setLevel(logging.DEBUG)


class UtilityFunction(object):
    """
    An object to compute the acquisition functions.
    """

    def __init__(self, kind, kappa, xi):
        """
        If UCB is to be used, a constant kappa is needed.
        """
        self.kappa = kappa

        self.xi = xi

        if kind not in ['ucb', 'ei', 'poi']:
            err = "The utility function " \
                  "{} has not been implemented, " \
                  "please choose one of ucb, ei, or poi.".format(kind)
            raise NotImplementedError(err)
        else:
            self.kind = kind

    def utility(self, x, gp, y_max):
        if self.kind == 'ucb':
            return UtilityFunction._ucb(x, gp, self.kappa)
        if self.kind == 'ei':
            return UtilityFunction._ei(x, gp, y_max, self.xi)
        if self.kind == 'poi':
            return UtilityFunction._poi(x, gp, y_max, self.xi)

    @staticmethod
    def _ucb(x, gp, kappa):
        mean, std = gp.predict(x, return_std=True)
        return mean + kappa * std

    @staticmethod
    def _ei(x, gp, y_max, xi):
        mean, std = gp.predict(x, return_std=True)
        z = (mean - y_max - xi) / std
        return (mean - y_max - xi) * norm.cdf(z) + std * norm.pdf(z)

    @staticmethod
    def _cei(x, gp, y_max, xi):  # TODO: Implement the constrained EI.
        pass

    @staticmethod
    def _poi(x, gp, y_max, xi):
        mean, std = gp.predict(x, return_std=True)
        z = (mean - y_max - xi) / std
        return norm.cdf(z)


def acq_max(ac, gp, y_max, bounds):
    """
    A function to find the maximum of the acquisition function

    It uses a combination of random sampling (cheap) and the 'L-BFGS-B'
    optimization method. First by sampling 1e5 points at random, and then
    running L-BFGS-B from 250 random starting points.

    Parameters
    ----------
    :param ac:
        The acquisition function object that return its point-wise value.

    :param gp:
        A gaussian process fitted to the relevant data.

    :param y_max:
        The current maximum known value of the target function.

    :param bounds:
        The variables bounds to limit the search of the acq max.


    Returns
    -------
    :return: x_max, The arg max of the acquisition function.
    """

    # Warm up with random points
    x_tries = np.random.uniform(bounds[:, 0], bounds[:, 1],
                                size=(100000, bounds.shape[0]))
    ys = ac(x_tries, gp=gp, y_max=y_max)
    x_max = x_tries[ys.argmax()]
    max_acq = ys.max()

    # Explore the parameter space more throughly
    x_seeds = np.random.uniform(bounds[:, 0], bounds[:, 1],
                                size=(250, bounds.shape[0]))
    for x_try in x_seeds:
        # Find the minimum of minus the acquisition function
        res = minimize(lambda x: -ac(x.reshape(1, -1), gp=gp, y_max=y_max),
                       x_try.reshape(1, -1),
                       bounds=bounds,
                       method="L-BFGS-B")

        # Store it if better than previous minimum(maximum).
        if max_acq is None or -res.fun[0] >= max_acq:
            x_max = res.x
            max_acq = -res.fun[0]

    # Clip output to make sure it lies within the bounds. Due to floating
    # point technicalities this is not always the case.
    return np.clip(x_max, bounds[:, 0], bounds[:, 1])


def unique_rows(a):
    """
    A functions to trim repeated rows that may appear when optimizing.
    This is necessary to avoid the sklearn GP object from breaking

    :param a: array to trim repeated rows from

    :return: mask of unique rows
    """

    # Sort array and kep track of where things should go back to
    order = np.lexsort(a.T)
    reorder = np.argsort(order)

    a = a[order]
    diff = np.diff(a, axis=0)
    ui = np.ones(len(a), 'bool')
    ui[1:] = (diff != 0).any(axis=1)

    return ui[reorder]


def get_candidate(X, y, bounds, acq='ucb', kappa=5, xi=0.0, **gp_params):
    """ Compute the next trials based on Bayesian Optimization.
    Args:
        X(numpy 2d array): rows of input feature vector
        y(numpy 1d array): array of target value
        bounds(array of tuples): i.e. [(x_lo, x_hi), (y_lo, y_hi), (z_lo, z_hi)]

    """

    # Set boundary
    bounds = np.asarray(bounds)

    # Initialize gaussian process regressor
    gp = GaussianProcessRegressor(
        kernel=Matern(nu=2.5),
        n_restarts_optimizer=25,
    )
    gp.set_params(**gp_params)

    # Initialize utiliy function
    util = UtilityFunction(kind=acq, kappa=kappa, xi=xi)

    # Find unique rows of X to avoid GP from breaking
    ur = unique_rows(X)
    log.debug(ur)
    log.debug("Fitting Gaussian Processor Regressor")
    gp.fit(X[ur], y[ur])

    # Finding argmax of the acquisition function.
    # TODO: Support multiple candidates of x_max
    log.debug("Computing argmax_x of acquisition function")
    y_max = y.max()
    x_max = acq_max(ac=util.utility,
                    gp=gp,
                    y_max=y_max,
                    bounds=bounds)

    return x_max
