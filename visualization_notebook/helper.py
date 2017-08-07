import matplotlib.pyplot as plt
import numpy as np
from matplotlib import gridspec


# plot helper functions
def posterior(gp, x):
    return gp.predict(x, return_std=True)


def plot_gp(gp, x, y, util, xlim=(-2, 10)):

    fig = plt.figure(figsize=(16, 10))
    fig.suptitle('Gaussian Process and Utility Function After {} Steps'.format(len(gp.X_train_)), fontdict={'size': 30})

    gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1])
    axis = plt.subplot(gs[0])
    acq = plt.subplot(gs[1])

    mu, sigma = posterior(gp, x)
    axis.plot(x, y, linewidth=3, label='Target')
    axis.plot(gp.X_train_.flatten(), gp.y_train_, 'D', markersize=8, label=u'Observations', color='r')
    axis.plot(x, mu, '--', color='k', label='Prediction')

    axis.fill(np.concatenate([x, x[::-1]]),
              np.concatenate([mu - y.max() * sigma, (mu + y.max() * sigma)[::-1]]),
              alpha=.6, fc='c', ec='None', label='95% confidence interval')

    axis.set_xlim(xlim)
    axis.set_ylim((None, None))
    axis.set_ylabel('f(x)', fontdict={'size': 20})
    axis.set_xlabel('x', fontdict={'size': 20})

    utility = util.utility(x, gp, gp.y_train_.max())

    acq.plot(x, utility, label='Utility Function', color='purple')
    acq.plot(x[np.argmax(utility)], np.max(utility), '*', markersize=15,
             label=u'Next Best Guess', markerfacecolor='gold', markeredgecolor='k', markeredgewidth=1)
    acq.set_xlim(xlim)
    acq.set_ylim((0, np.max(utility) * 1.2))
    acq.set_ylabel('Utility', fontdict={'size': 20})
    acq.set_xlabel('x', fontdict={'size': 20})

    axis.legend(loc=2, bbox_to_anchor=(1.01, 1), borderaxespad=0.)
    acq.legend(loc=2, bbox_to_anchor=(1.01, 1), borderaxespad=0.)


def plot_gps(gp_y, gp_c, x, y, c, util_ei, util_cei, constraint_upper, xlim=(-2,10)):

    fig = plt.figure(figsize=(16, 10))
    fig.suptitle('Gaussian Process and Utility Function After {} Steps'.format(
        len(gp_y.X_train_)), fontdict={'size': 30})

    gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1])
    axis = plt.subplot(gs[0])
    acq = plt.subplot(gs[1])

    # posterior of target function estimation
    mu_y, sigma_y = posterior(gp_y, x)
    axis.plot(x, y, linewidth=3, label='Target', color='lightblue')
    axis.plot(gp_y.X_train_.flatten(), gp_y.y_train_, 'D', markersize=8, label=u'Target Observations', color='r')
    axis.plot(x, mu_y, '--', color='lightblue', label='Target Prediction')

    axis.fill(np.concatenate([x, x[::-1]]),
              np.concatenate([mu_y - 1.9600 * sigma_y, (mu_y + 1.9600 * sigma_y)[::-1]]),
              alpha=.3, fc='c', ec='None', label='95% confidence interval', color='lightblue')

    axis.set_xlim(xlim)
    axis.set_ylim((None, None))
    axis.set_ylabel('f(x)', fontdict={'size': 20})
    axis.set_xlabel('x', fontdict={'size': 20})

    # posterior of constraint function estimation
    mu_c, sigma_c = posterior(gp_c, x)
    axis.plot(x, c, linewidth=3, label='Target', color='y')
    axis.plot(gp_c.X_train_.flatten(), gp_c.y_train_, 'D', markersize=8, label=u'Constraint Observations', color='r')
    axis.plot(x, mu_c, '--', color='y', label='Constraint Prediction')

    axis.fill(np.concatenate([x, x[::-1]]),
              np.concatenate([mu_c - 1.9600 * sigma_c, (mu_c + 1.9600 * sigma_c)[::-1]]),
              alpha=.3, fc='c', ec='None', label='95% confidence interval', color='y')

    axis.set_xlim(xlim)
    axis.set_ylim((None, None))
    axis.set_xlabel('x', fontdict={'size': 20})

    # constraint upper bound
    axis.plot(x, [constraint_upper] * len(x), label='constraint_upper', color='k')

    utility = util_ei.utility(x)  # 0???
    utility_cei = util_cei.utility(x)  # 0???

    acq.plot(x, utility, label='Utility Function EI', color='r', alpha=.3)
    acq.plot(x[np.argmax(utility)], np.max(utility), '*', markersize=15,
             label=u'Next Best Guess', markerfacecolor='gold', markeredgecolor='k', markeredgewidth=1)

    acq.plot(x, utility_cei, label='Utility Function CEI', color='g', alpha=.3)
    acq.plot(x[np.argmax(utility_cei)], np.max(utility_cei), '*', markersize=15,
             label=u'Next Best Guess', markerfacecolor='gold', markeredgecolor='k', markeredgewidth=1)
    acq.set_xlim(xlim)
    acq.set_ylim((0, np.max(np.hstack((utility, utility_cei)) * 1.2)))
    acq.set_xlabel('x', fontdict={'size': 20})

    axis.legend(loc=2, bbox_to_anchor=(1.01, 1), borderaxespad=0.)
    acq.legend(loc=2, bbox_to_anchor=(1.01, 1), borderaxespad=0.)
