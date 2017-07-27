from __future__ import print_function
from __future__ import division

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern
from scipy.stats import norm
from scipy.optimize import minimize
from logger import get_logger

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

    def utility(self, x, gp_objective, y_max, constraint=None, mean=None, std=None, bounds=None, gp_constraint=None):
        if self.kind == 'ucb':
            return UtilityFunction._ucb(x, gp_objective, self.kappa)
        if self.kind == 'ei':
            return UtilityFunction._ei(x, gp_objective, y_max, self.xi)
        if self.kind == 'cei_analytic':
            assert constraint is not None, 'constraint must be provided'
            assert mean is not None, 'mean must be provided'
            assert std is not None, 'std must be provided'
            return UtilityFunction._cei_analytic(x, gp_objective, y_max, self.xi, constraint, mean, std)
        if self.kind == 'cei_numeric':
            assert constraint is not None, 'constraint must be provided'
            assert bounds is not None, 'bounds must be provided'
            assert gp_constraint is not None, 'gaussian processor of constraint must be provided'
            return UtilityFunction._cei_numeric(x, gp_objective, y_max, self.xi, constraint, bounds, gp_constraint)
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
    def _cei_analytic(x, gp_objective, y_max, xi, constraint, mean, std):
        """ Compute the cdf under constraint (i.e. P(c < constraint)).
        Assume the marginal distribution P(c) = \int_x P(c,x)dx is a normal distribution Norm(mean, std)
        So the cdf can be computed analytically.
        """
        ei = UtilityFunction._ei(x, gp_objective, y_max, xi)
        z = (constraint - mean) / std
        cumulative_probabiliy = norm.cdf(z)
        return cumulative_probabiliy * ei

    @staticmethod
    def _cei_numeric(x, gp_objective, y_max, xi, constraint, bounds, gp_constraint):
        """ Compute the cdf under constraint (i.e. P(c < constraint)).
            Compute the cumulative probability (i.e. P(c < constraint)) of a gaussian process.
            Estimate by uniform sampling in feature space, to derive each cdf, then average over all cdf
        """
        ei = UtilityFunction._ei(x, gp_objective, y_max, xi)
        mean, std = gp_constraint.predict(x, return_std=True)
        z = (constraint - mean) / std
        cumulative_probabiliy = norm.cdf(z)
        return cumulative_probabiliy * ei

    @staticmethod
    def _poi(x, gp_objective, y_max, xi):
        mean, std = gp_objective.predict(x, return_std=True)
        z = (mean - y_max - xi) / std
        return norm.cdf(z)


def acq_max(ac, gp_objective, y_max, bounds, constraint=None, mean=None, std=None, gp_constraint=None):
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
            constraint=constraint, mean=mean, std=std, gp_constraint=gp_constraint, bounds=bounds)
    x_max = x_tries[ys.argmax()]
    max_acq = ys.max()

    # Explore the parameter space more throughly
    x_seeds = np.random.uniform(bounds[:, 0], bounds[:, 1],
                                size=(250, bounds.shape[0]))
    for x_try in x_seeds:
        # Find the minimum of minus the acquisition function
        res = minimize(lambda x: -ac(x.reshape(1, -1), gp_objective=gp_objective, y_max=y_max,
                                     constraint=constraint, mean=mean, std=std, gp_constraint=gp_constraint, bounds=bounds),
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


def get_candidate(features, objectives, bounds, acq='cei_analytic', constraints=None, kappa=5, xi=0.0, constraint=None, **gp_params):
    """ Compute the next candidate based on Bayesian Optimization
    Args:
        features(numpy 2d array): feature vectors
        objectives(numpy 1d array): objective values
        bounds(array of tuples): output will be cliped by bounds. i.e. bounds=[(x1_lo, x1_hi), (x2_lo, x2_hi), (x3_lo, x3_hi)]
    Return:
        argmax(vector): argmax of acquisition function
    """
    # Set boundary
    bounds = np.asarray(bounds)

    # Initialize gaussian process regressor for objective function
    gp_objective = GaussianProcessRegressor(
        kernel=Matern(nu=2.5),
        n_restarts_optimizer=25,
    )
    gp_objective.set_params(**gp_params)

    # Initialize utiliy function
    util = UtilityFunction(kind=acq, kappa=kappa, xi=xi)

    # Find unique rows of X to avoid GP from breaking
    ur = unique_rows(features)
    logger.debug("Fitting Gaussian Processor Regressor")
    gp_objective.fit(features[ur], objectives[ur])

    # Finding argmax of the acquisition function.
    logger.debug("Computing argmax_x of acquisition function")
    y_max = objectives.max()

    if acq == 'cei_analytic':
        assert constraint is not None
        assert constraints is not None
        mean = np.mean(constraints, axis=0)
        std = np.std(constraints, axis=0)
        argmax = acq_max(ac=util.utility,
                         gp_objective=gp_objective,
                         y_max=y_max,
                         bounds=bounds,
                         constraint=constraint,
                         mean=mean,
                         std=std)
    elif acq == 'cei_numeric':
        assert constraint is not None
        assert constraints is not None
        gp_constraint = GaussianProcessRegressor(
            kernel=Matern(nu=2.5),
            n_restarts_optimizer=25,
        )
        gp_constraint.set_params(**gp_params)
        # Find unique rows of X to avoid GP from breaking
        ur = unique_rows(features)
        logger.debug(ur)
        logger.debug("Fitting Gaussian Processor Regressor")
        gp_constraint.fit(features[ur], constraints[ur])

        argmax = acq_max(ac=util.utility,
                         gp_objective=gp_objective,
                         y_max=y_max,
                         bounds=bounds,
                         constraint=constraint,
                         gp_constraint=gp_constraint
                         )
    else:
        argmax = acq_max(ac=util.utility,
                         gp_objective=gp_objective,
                         y_max=y_max,
                         bounds=bounds,
                         )

    return argmax
