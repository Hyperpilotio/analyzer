# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from pymongo import MongoClient
from single_app import views as single_app_views
from core.mongo_util import get_available_apps


@csrf_exempt
def echo(request):
    if request.method == 'POST':
        response = JsonResponse(json.loads(request.body))
    else:
        response = JsonResponse({'Exception':
                                 "Unsupported request method: {}".format(request.method)})
    return response


@csrf_exempt
def connect_db(request):
    try:
        client = MongoClient(settings.DATABASE_URL)
        metric_db = client[settings.METRIC_DB]
        assert metric_db.authenticate(settings.USER, settings.PWD,
                                      source=settings.METRIC_DB), 'Cannot get authentication from MetricDB'
        config_db = client[settings.CONFIG_DB]
        assert config_db.authenticate(settings.USER, settings.PWD,
                                      source=settings.CONFIG_DB), 'Cannot get authentication from ConfigDB'
    except Exception as e:
        return JsonResponse({'Exception': str(e)}, status=500)

    else:
        return JsonResponse({'connect_db': 'OK'})


def empty(request):
    return render(request, 'core/empty.html', {'apps': set(get_available_apps(collection='profiling'))})

