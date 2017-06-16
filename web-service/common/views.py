# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from pymongo import MongoClient
from common.mongoUtil import getAvailableApps


@csrf_exempt
def echo(request):
    if request.method == 'POST':
        response = JsonResponse(json.loads(request.body))
    else:
        response = JsonResponse({'Exception':
                                 "Unsupported request method: {}".format(request.method)})
    return response


@csrf_exempt
def connectToDB(request):
    try:
        client = MongoClient(settings.DATABASE_URL)
        metricDb = client[settings.METRIC_DB]
        assert metricDb.authenticate(settings.USER, settings.PWD,
                                     source=settings.METRIC_DB), 'Cannot get authentication from MetricDB'
        configDb = client[settings.CONFIG_DB]
        assert configDb.authenticate(settings.USER, settings.PWD,
                                     source=settings.CONFIG_DB), 'Cannot get authentication from ConfigDB'
    except Exception as e:
        return JsonResponse({'Exception': str(e)}, status=500)

    else:
        return JsonResponse({'connect to mongoDB': 'OK'})


def empty(request):
    return render(request, 'common/empty.html',
                  {'calibrationApps': getAvailableApps(collection='calibration'),
                   'profilingApps': getAvailableApps(collection='profiling'),
                   'validationApps': getAvailableApps(collection='validation')})
