from __future__ import division, print_function

import numpy as np
from logger import get_logger
from scipy.optimize import minimize
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern

logger = get_logger(__name__, log_level=("BAYESIAN_OPTIMIZER", "LOGLEVEL"))


class UtilityFunction(object):
    """ An object to compute the acquisition functions.
    """

    def __init__(self, kind, gp_objective, gp_constraint=None, constraint_upper=None, xi=0.0, kappa=5.):
        """ If UCB is to be used, a constant kappa is needed.
        """
        self.implementations = ['ucb', 'ei', 'cei', 'poi']
        if kind not in self.implementations:
            err = f"The utility function {kind} has not been implemented, " \
                "please choose one of ucb, ei, cei, or poi."
            raise NotImplementedError(err)
        else:
            self.kind = kind

        self.gp_objective = gp_objective
        self.gp_constraint = gp_constraint
        self.xi = xi
        self.kappa = kappa
        self.constraint_upper = constraint_upper

    def utility(self, x):
        gp_objective = self.gp_objective
        gp_constraint = self.gp_constraint
        constraint_upper = self.constraint_upper
        xi, kappa = self.xi, self.kappa

        if self.kind == 'ucb':
            return UtilityFunction._ucb(x, gp_objective, kappa)
        if self.kind == 'ei':
            return UtilityFunction._ei(x, gp_objective, xi)
        if self.kind == 'cei':
            assert gp_constraint is not None, 'gaussian processor of constraint must be provided'
            assert constraint_upper is not None, 'constraint_upper must be provided'
            return UtilityFunction._cei(x, gp_objective, xi, gp_constraint, constraint_upper)
        if self.kind == 'poi':
            return UtilityFunction._poi(x, gp_objective, xi)

    @staticmethod
    def _ucb(x, gp_objective, kappa):
        mean, std = gp_objective.predict(x, return_std=True)
        return mean + kappa * std

    @staticmethod
    def _ei(x, gp_objective, xi):
        y_max = gp_objective.y_train_.max()
        mean, std = gp_objective.predict(x, return_std=True)
        z = (mean - y_max - xi) / std
        return (mean - y_max - xi) * norm.cdf(z) + std * norm.pdf(z)

    @staticmethod
    def _cei(x, gp_objective, xi, gp_constraint, constraint_upper):
        """ Compute the cdf under constraint_upper (i.e. P(c(x) < constraint_upper)) modualte the ei(x).
            whereas c(x) is a estimated gaussian distribution.
        """
        y_max = gp_objective.y_train_.max()
        ei = UtilityFunction._ei(x, gp_objective, xi)

        mean, std = gp_constraint.predict(x, return_std=True)
        z = (constraint_upper - mean) / std
        cumulative_probabiliy = norm.cdf(z)
        return cumulative_probabiliy * ei

    @staticmethod
    def _poi(x, gp_objective, xi):
        y_max = gp_objective.y_train_.max()
        mean, std = gp_objective.predict(x, return_std=True)
        z = (mean - y_max - xi) / std
        return norm.cdf(z)


def acq_max(utility, bounds):
    """ A function to find the maximum of the acquisition function
        It uses a combination of random sampling (cheap) and the 'L-BFGS-B'
        optimization method. First by sampling 1e5 points at random, and then
        running L-BFGS-B from 250 random starting points.
    Args:
        ac: The acquisition function object that return its point-wise value.
        gp_objective: A gaussian process fitted to the relevant data.
        y_max: The current maximum known value of the target function.
        bounds: The variables bounds to limit the search of the acq max.
    Returns
        x_max: The arg max of the acquisition function.
    """
    
    # Warm up with random points
    x_tries = np.random.uniform(bounds[:, 0], bounds[:, 1],
                                size=(100000, bounds.shape[0]))
    ys = utility(x_tries)
    x_max = x_tries[ys.argmax()]
    max_acq = ys.max()

    # Explore the parameter space more throughly
    x_seeds = np.random.uniform(bounds[:, 0], bounds[:, 1],
                                size=(250, bounds.shape[0]))
    for x_try in x_seeds:
        # Find the minimum of minus the acquisition function
        res = minimize(lambda x: -utility(x.reshape(1, -1)), x_try.reshape(1, -1),
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
    """ A functions to trim repeated rows that may appear when optimizing.
        This is necessary to avoid the sklearn GP object from breaking
    Args:
        a(array): array to trim repeated rows from
    Return:
        mask of unique rows
    """
    # Sort array and kep track of where things should go back to
    order = np.lexsort(a.T)
    reorder = np.argsort(order)

    a = a[order]
    diff = np.diff(a, axis=0)
    ui = np.ones(len(a), 'bool')
    ui[1:] = (diff != 0).any(axis=1)

    return ui[reorder]


def get_fitted_gaussian_processor(X_train, y_train, **gp_params):
    # Initialize gaussian process regressor
    gp = GaussianProcessRegressor()
    gp.set_params(**gp_params)
    logger.debug('Instantiated gaussian processor for objective function:\n' + f'{gp}')
    # Find unique rows of X to avoid GP from breaking
    ur = unique_rows(X_train)
    logger.debug(f"Fitting gaussian processor")
    gp.fit(X_train[ur], y_train[ur])
    logger.debug(f'Done.')
    return gp


def get_candidate(feature_mat, objective_arr, bounds, acq,
                  constraint_arr=None, constraint_upper=None,
                  kappa=5, xi=0.0, **gp_params):
    """ Compute the next candidate based on Bayesian Optimization
    Args:
        feature_mat(numpy 2d array): feature vectors
        objective_arr(numpy 1d array): objective values
        bounds(array of tuples): the searching boundary of feature space
            i.e. bounds=[(x1_lo, x1_hi), (x2_lo, x2_hi), (x3_lo, x3_hi)]
        acq(str): kind of acquisition function

    Return:
        argmax(vector): argmax of acquisition function
    """
    # TODO: Put these into config file
    seed = 6
    gp_params = {"alpha": 1e-5, "n_restarts_optimizer": 25,
                 "kernel": Matern(nu=2.5), "random_state": seed}
    # Set boundary
    bounds = np.asarray(bounds)

    gp_objective = get_fitted_gaussian_processor(
        feature_mat, objective_arr, **gp_params)
    if (constraint_arr is not None) and (constraint_upper is not None):
        gp_constraint = get_fitted_gaussian_processor(
            feature_mat, constraint_arr, **gp_params)
    else:
        gp_constraint, constraint_upper = None, None

    # Initialize utiliy function
    util = UtilityFunction(kind=acq, gp_objective=gp_objective, gp_constraint=gp_constraint,
                           constraint_upper=constraint_upper, xi=xi, kappa=kappa)

    # Finding argmax of the acquisition function.
    logger.debug("Computing argmax of acquisition function")
    argmax = acq_max(utility=util.utility, bounds=bounds)

    return argmax
