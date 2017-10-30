# %%
import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import gridspec
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, RBF
from matplotlib import cm

import util
from analyzer import bayesian_optimizer
from analyzer.bayesian_optimizer_pool import BayesianOptimizerPool as BOP

%matplotlib inline

# %% Load dataframe
df = pd.read_pickle('cloud_perf_b8000.0.pkl')
df
# %% sort by qos/cost
df.sort_values('qos_over_cost', ascending=False)

# %% sort by qos
df.sort_values('qos', ascending=True)

# %% sort by cost vs qos/cost
df = df.sort_values('cost', ascending=False)
plt.scatter(df['cost'], df['qos_over_cost'])
# %% sort by cost vs cost
plt.scatter(df['cost'], df['qos'])
# %% feature 0 vs qos
plt.scatter(df.feature.apply(lambda x: x[0]), df.qos)
plt.title('feature 0 vs qos')

# %% feature 1 vs qos
plt.scatter(df.feature.apply(lambda x: x[1]), df.qos)
plt.title('feature 1 vs qos')
# %% feature 2 vs qos
plt.scatter(df.feature.apply(lambda x: x[2]), df.qos)
plt.title('feature 2 vs qos')
# %% feature 3 vs qos
plt.scatter(df.feature.apply(lambda x: x[3]), df.qos)
plt.title('feature 3 vs qos')
# %% feature 4 vs qos
plt.scatter(df.feature.apply(lambda x: x[4]), df.qos)
plt.title('feature 4 vs qos')


# %% distance of our normalized feature space
df = df.sort_values('cost')
features = df['nodetype'].apply(util.encode_nodetype)
n = len(df['nodetype'])
heatmap = np.zeros((n, n))
for i in range(n):
    for j in range(n):
        heatmap[i, j] = util.feature_distance(features[i], features[j])

plt.matshow(heatmap, cmap='gray')
plt.savefig('distance.pdf', format='pdf')

# %% Different init
# np.random.seed(6)
init_points = BOP.generate_initial_points(10)
print('\n==init_points:')
print(init_points)

feature_mat = np.array([util.encode_nodetype(n) for n in init_points])
bounds = util.get_feature_bounds(normalized=True)
acq = 'ei'
selected = pd.concat([df[df['nodetype'] == n] for n in init_points])
objective_arr = selected['qos_over_cost']


candidate = bayesian_optimizer.get_candidate(feature_mat, objective_arr, bounds,
                                             acq=acq, constraint_arr=None,
                                             constraint_upper=None)
print('candidate:')
print(candidate)
print('decoded:')
print(util.decode_nodetype(candidate))
print('\n')


# %% iterates
from importlib import reload
reload(bayesian_optimizer)
np.set_printoptions(precision=5)
niter = 3
init_points = BOP.generate_initial_points(3)
print('\n==init_points:')
print(init_points)

selected = pd.concat([df[df['nodetype'] == n] for n in init_points])

X_train = np.array([util.encode_nodetype(n) for n in init_points])
y_train = selected['qos_over_cost']
bounds = util.get_feature_bounds(normalized=True)
acq = 'ei'

candidates = []
X_train_ = np.array(X_train)
y_train_ = np.array(y_train)

for i in range(niter):
    candidate = bayesian_optimizer.get_candidate(X_train_, y_train_, bounds,
                                                 acq=acq, constraint_arr=None,
                                                 constraint_upper=None)

    y = df[df['nodetype'] == util.decode_nodetype(candidate)]['qos'].values[0]
    X_train_ = np.vstack(
        (X_train_, np.array([util.encode_nodetype(util.decode_nodetype(candidate))])))
    y_train_ = np.hstack((y_train_, y))
    print('====')
    print(candidate)
    print(y)

    candidates.append(util.decode_nodetype(candidate))


# print(X_train_)
# print(y_train_)
# print(candidates)


# %%
def target(x):
    return np.exp(-(x - 2)**2) + np.exp(-(x - 6)**2/10) + 1/ (x**2 + 1)

# %% gp
X_train_ = np.array(X_train)[:5, 0:1]
y_train_ = [target(x)[0] for x in X_train_]
M = Matern(nu=2.5)
# B = RBF(length_scale=1.)
# print(B)
np.set_printoptions(precision=5)
print(M)
print(f'X_train : {X_train_}')
print(f'y_train : {y_train_}')

# %%
gp_params = {"alpha": 0, "n_restarts_optimizer": 25,
             "kernel": M, "random_state": 6, "normalize_y": False}

# X_train_ = np.random.rand(*X_train.shape)
# y_train_ = np.random.rand(len(y_train))

# print(X_train_)
# print(y_train_)

bounds = np.array(util.get_feature_bounds(normalized=True))

gp = bayesian_optimizer.get_fitted_gaussian_processor(
    X_train_, np.array(y_train_), **gp_params)

# print(bounds)


for i in range(len(X_train_)):
    print(f"======{i}")
    print(f'X_train: {X_train_[i]}\ny_train: {y_train_[i]}')
    for j in range(2):
        print('----')

        x_hat = X_train_[i]
        if j != 0:
            x_hat = np.multiply(
                x_hat, np.random.uniform(10, 10, size=(1, len(x_hat))))

        x_hat = np.array(x_hat)

        mean, std = gp.predict(x_hat, return_std=True)
        print('-p predict x_hat')
        print(f'x_hat: {x_hat}')
        print(f'mean: {mean}, std: {std}')
