# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import numpy as np
import pandas as pd
from django.conf import settings
from django.db import models
from pymongo import MongoClient


def create_dataframe(app_name):
    """ Create a dataframe of features.
    Args:
        app_name(str): Map to the 'appName' in Mongo database.
    Returns:
        df(pandas dataframe): Dataframe with rows of features, where each row is a service.
        (i.e. if an app has N services, where each service has K dimensions, the dataframe would be NxK)
    """
    # TODO: Load data from MetricDB
    service_names = pd.Index(['mysql', 'nginx'])
    feature_names = pd.Index(['cpu', 'memCap', 'memBw'])

    # TODO: Make dataframe
    df = pd.DataFrame(data=np.random.rand(len(service_names), len(
        feature_names)), index=service_names, columns=feature_names)
    return df


class LinearRegression1():
    """ Linear Regression1
    Each service is described a feature vector of ibench profiling results
    (i.e service_i = [s_i1, s_i2, ..., s_ik], where k is number of ibenchmark tests)

    This model assumes the Cross-App Interference is the result of the linear combination of
    the elementwise-product of two services i and j.
    (i.e. CAIS_ij = w_0 + w_1*s_i1*s_j1 + w_2*s_i2*s_j2 + ... + w_k*s_ik*s_jk)

    """

    def __init__(self, num_dims):
        self.parameters = np.zeros(num_dims + 1)  # with bias

    def _predict_service(self, feature1, feature2):
        # assume the first parameter is bias
        return np.sum(reduce(np.multiply, [self.parameters[1:], feature1, feature2])) + self.parameters[0]

    def load(self, filename='lr1_parameters.npy'):
        # TODO: Load real parameters
        self.parameters = np.load(filename)

    def save(self, filename='lr1_parameters.npy'):
        # TODO: Save somewhere else?
        np.save(filename, self.parameters)

    def fit(self, data, target):
        # TODO: fit the data...
        self.parameters = np.random.rand(len(self.parameters))
        return self

    def predict(self, app1_name, app2_name):
        """ Construct the CAIS matrix.
        Args:
            app_name(str): Map to the 'appName' in Mongo database.
        Returns:
            cais_dataframe(pandas dataframe): NxK matrix where N, K are number of services of app1 and app2.
        """
        df1, df2 = create_dataframe(app1_name), create_dataframe(app2_name)
        df1.name, df2.name = app1_name, app2_name

        cais_matrix = np.zeros((len(df1.index), len(df2.index)))

        for i, (service_i, feature_i) in enumerate(df1.iterrows()):
            for j, (service_j, feature_j) in enumerate(df2.iterrows()):
                cais_matrix[i, j] = self._predict_service(feature_i, feature_j)

        cais_dataframe = pd.DataFrame(data=cais_matrix, index=pd.Index(
            df1.index.values), columns=pd.Index(df2.index.values))

        return cais_dataframe

    def validate(self, data, target, loss_metric='mse'):
        # TODO: implement it.
        pass
