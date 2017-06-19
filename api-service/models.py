import numpy as np
import pandas as pd
from .db import metricdb


#TODO: probably need to change to app_id.
def create_profiling_dataframe(app_name):
    """ Create a dataframe of features.
    Args:
        app_name(str): Map to the 'appName' in Mongo database.
    Returns:
        df(pandas dataframe): Dataframe with rows of features, where each row is a service.
        (i.e. if an app has N services, where each service has K dimensions, the dataframe would be NxK)
    """
    filt = {'appName': app_name}
    app = metricdb.profiling.find_one(filt)
    if app == None:
        raise KeyError(f"Cannot find document: filter={filt}")
    service_names = pd.Index(app['services'])
    benchmark_names = pd.Index(app['benchmarks'])

    # make dataframe
    ibench_scores = []
    for service in service_names:
        {'appName': app_name, 'serviceInTest': service}
        metricdb.profiling.find_one(filt)
        # app = find_one(collection='profiling', filt=filt)
        if app == None:
            raise KeyError(f"Cannot find document: filter={filt}")
        ibench_scores.append([i['toleratedInterference']
                              for i in app['testResult']])
    df = pd.DataFrame(data=np.array(ibench_scores),
                      index=service_names, columns=benchmark_names)
    return df


class LinearRegression1():
    """ Linear Regression1
    Each service is described a feature vector of ibench profiling results
    (i.e service_i = [s_i1, s_i2, ..., s_ik], where k is number of ibenchmark tests)

    This model assumes the Cross-App Interference is the result of the linear combination of
    the elementwise-product of two services i and j.
    (i.e. CAIS_ij = w_0 + w_1*s_i1*s_j1 + w_2*s_i2*s_j2 + ... + w_k*s_ik*s_jk)

    """

    def __init__(self, numDims):
        self.parameters = np.zeros(numDims + 1)  # with bias

    def _predictService(self, feature1, feature2):
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

    def predict(self, app1Name, app2Name, collection):
        """ Construct the CAIS matrix.
        Args:
            appName(str): Map to the 'appName' in Mongo database.
        Returns:
            caisDataframe(pandas dataframe): NxK matrix where N, K are number of services of app1 and app2.
        """
        collection = 'profiling' if not collection else collection

        df1, df2 = createProfilingDataframe(
            app1Name, collection), createProfilingDataframe(app2Name, collection)
        df1.name, df2.name = app1Name, app2Name
        print(df1)
        print(df2)

        caisMatrix = np.zeros((len(df1.index), len(df2.index)))

        for i, (service_i, feature_i) in enumerate(df1.iterrows()):
            for j, (service_j, feature_j) in enumerate(df2.iterrows()):
                caisMatrix[i, j] = self._predictService(feature_i, feature_j)

        caisDataframe = pd.DataFrame(data=caisMatrix, index=pd.Index(
            df1.index.values), columns=pd.Index(df2.index.values))

        return caisDataframe

    def validate(self, data, target, lossMetric='mse'):
        # TODO: implement it.
        pass
