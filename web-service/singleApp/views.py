# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings
from bson.objectid import ObjectId
import common.mongoUtil as mu


def _getApps():
    """ Get available apps from metricDB collections.
    """
    apps = {'calibrationApps': mu.getAvailableApps(collection='calibration'),
            'profilingApps': mu.getAvailableApps(collection='profiling'),
            'validationApps': mu.getAvailableApps(collection='validation')}
    return apps


def calibration(request, appId):
    template = _getApps()
    # find appName by appId
    document = mu.findOne(collection='calibration',
                          database=settings.METRIC_DB,
                          filt={'_id': ObjectId(appId)})
    document['appId']=document['_id']
    template['document'] = document
    assert document, 'document id {} is not found in calibration collection'.format(
        appId)
    return render(request, 'singleApp/calibration.html', template)


def profiling(request, appId):
    template = _getApps()
    # find appName by appId
    document = mu.findOne(collection='profiling',
                          database=settings.METRIC_DB,
                          filt={'_id': ObjectId(appId)})
    document['appId']=document['_id']
    template['document'] = document
    assert document, 'document id {} is not found in profiling collection'.format(
        appId)
    return render(request, 'singleApp/profiling.html', template)
