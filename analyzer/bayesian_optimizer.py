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

    def __init__(self, kind, xi=0.0, kappa=5.):
        """ If UCB is to be used, a constant kappa is needed.
        """
        self.xi = xi
        self.kappa = kappa
        self.implementations = ['ucb', 'ei',
                                'cei_analytic', 'cei_numeric', 'poi']

        if kind not in self.implementations:
            err = f"The utility function " \
                "{kind} has not been implemented, " \
                "please choose one of ucb, ei, or poi."
            raise NotImplementedError(err)
        else:
            self.kind = kind

    def utility(self, x, gp_objective, y_max, gp_constraint=None, constraint_upper=None):
        if self.kind == 'ucb':
            return UtilityFunction._ucb(x, gp_objective, self.kappa)
        if self.kind == 'ei':
            return UtilityFunction._ei(x, gp_objective, y_max, self.xi)
        if self.kind == 'cei':
            assert gp_constraint is not None, 'gaussian processor of constraint must be provided'
            assert constraint_upper is not None, 'constraint_upper must be provided'
            return UtilityFunction._cei(x, gp_objective, y_max, self.xi, gp_constraint, constraint_upper)
        if self.kind == 'poi':
            return UtilityFunction._poi(x, gp_objective, y_max, self.xi)

    @staticmethod
    def _ucb(x, gp_objective, kappa):
        mean, std = gp_objective.predict(x, return_std=True)
        return mean + kappa * std

    @staticmethod
    def _ei(x, gp_objective, y_max, xi):
        mean, std = gp_objective.predict(x, return_std=True)
        z = (mean - y_max - xi) / std
        return (mean - y_max - xi) * norm.cdf(z) + std * norm.pdf(z)

    @staticmethod
    def _cei(x, gp_objective, y_max, xi, gp_constraint, constraint_upper):
        """ Compute the cdf under constraint_upper (i.e. P(c(x) < constraint_upper)) modualte the ei(x).
            whereas c(x) is a estimated gaussian distribution.
        """
        ei = UtilityFunction._ei(x, gp_objective, y_max, xi)
        mean, std = gp_constraint.predict(x, return_std=True)
        z = (constraint_upper - mean) / std
        cumulative_probabiliy = norm.cdf(z)
        return cumulative_probabiliy * ei

    @staticmethod
    def _poi(x, gp_objective, y_max, xi):
        mean, std = gp_objective.predict(x, return_std=True)
        z = (mean - y_max - xi) / std
        return norm.cdf(z)


def acq_max(ac, gp_objective, y_max, bounds, constraint_upper=None, mean=None, std=None, gp_constraint=None):
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
    ys = ac(x_tries, gp_objective=gp_objective, y_max=y_max,
            constraint_upper=constraint_upper, mean=mean, std=std, gp_constraint=gp_constraint, bounds=bounds)
    x_max = x_tries[ys.argmax()]
    max_acq = ys.max()

    # Explore the parameter space more throughly
    x_seeds = np.random.uniform(bounds[:, 0], bounds[:, 1],
                                size=(250, bounds.shape[0]))
    for x_try in x_seeds:
        # Find the minimum of minus the acquisition function
        res = minimize(lambda x: -ac(x.reshape(1, -1), gp_objective=gp_objective, y_max=y_max,
                                     constraint_upper=constraint_upper, mean=mean, std=std, gp_constraint=gp_constraint, bounds=bounds),
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
    """ A functions to trim repeated rows that may appear when optimizing. This is necessary to avoid the sklearn GP object from breaking
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

    # Initialize gaussian process regressor for objective function
    gp_objective = GaussianProcessRegressor()
    gp_objective.set_params(**gp_params)
    logger.debug(f'Instantiated gaussian processor for objective function:\n' + '{gp_objective}')

    # Initialize utiliy function
    util = UtilityFunction(kind=acq, kappa=kappa, xi=xi)

    # Find unique rows of X to avoid GP from breaking
    ur = unique_rows(feature_mat)
    logger.debug(f"Fitting Objective Gaussian Processor Regressor: {gp_objective}")
    gp_objective.fit(feature_mat[ur], objective_arr[ur])
    logger.debug(f'Done.')

    # Finding argmax of the acquisition function.
    logger.debug("Computing argmax of acquisition function")
    if acq == 'cei_numeric':
        assert constraint_upper is not None
        assert constraint_arr is not None
        gp_constraint = GaussianProcessRegressor()
        gp_constraint.set_params(**gp_params)
        logger.debug(f'Instantiated gaussian processor for constraint function:\n' + '{gp_objective}')
        # Find unique rows of X to avoid GP from breaking
        ur = unique_rows(feature_mat)
        logger.debug(f"Fitting Constraint Gaussian Processor Regressor: {gp_constraint}")
        gp_constraint.fit(feature_mat[ur], constraint_arr[ur])
        logger.debug(f'Done.')
        argmax = acq_max(ac=util.utility,
                         gp_objective=gp_objective,
                         y_max=objective_arr.max(),
                         bounds=bounds,
                         constraint_upper=constraint_upper,
                         gp_constraint=gp_constraint
                         )
    else:
        argmax = acq_max(ac=util.utility,
                         gp_objective=gp_objective,
                         y_max=objective_arr.max(),
                         bounds=bounds,
                         )

    return argmax
