from api_service.db import metricdb


# TODO: probably need to change to appId.
def createProfilingDataframe(appName, collection='profiling'):
    """ Create a dataframe of features.
    Args:
        appName(str): Map to the 'appName' in Mongo database.
    Returns:
        df(pandas dataframe): Dataframe with rows of features, where each row is a service.
        (i.e. if an app has N services, where each service has K dimensions, the dataframe would be NxK)
    """
    filt = {'appName': appName}
    app = metricdb[collection].find_one(filt)
    if app == None:
        raise KeyError(
            'Cannot find document: filter={}'.format(filt))
    serviceNames = pd.Index(app['services'])
    benchmarkNames = pd.Index(app['benchmarks'])

    # make dataframe
    ibenchScores = []
    for service in serviceNames:
        filt = {'appName': appName, 'serviceInTest': service}
        app = metricdb[collection].find_one(filt)
        if app == None:
            raise KeyError(
                'Cannot find document: filter={}'.format(filt))
        ibenchScores.append([i['toleratedInterference']
                             for i in app['testResult']])
    df = pd.DataFrame(data=np.array(ibenchScores),
                      index=serviceNames, columns=benchmarkNames)
    return df
