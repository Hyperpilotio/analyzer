# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings
from bson.objectid import ObjectId
import core.mongo_util as mu


def get_apps_helper():
    try:
        calibration_apps = mu.get_available_apps(collection='calibration')
        profiling_apps = mu.get_available_apps(collection='profiling')
        validation_apps = mu.get_available_apps(collection='validation')
        apps = {'calibration_apps': calibration_apps,
                'profiling_apps': profiling_apps,
                'validation_apps': validation_apps}
    except Exception as e:
        raise e
    else:
        return apps


def calibration(request, app_id):
    try:
        dictionary = get_apps_helper()
        # reverse for appName
        app_name = mu.find_one(collection='calibration',
                               database=settings.METRIC_DB, filt={'_id': ObjectId(app_id)})['appName']

        dictionary['app_name'] = app_name
    except Exception as e:
        return JsonResponse({'Exception': str(e)})
    else:
        return render(request, 'single_app/calibration.html', dictionary)


def profiling(request, app_id):
    try:
        dictionary = get_apps_helper()
        # reverse for appName
        app_name = mu.find_one(collection='profiling',
                               database=settings.METRIC_DB, filt={'_id': ObjectId(app_id)})['appName']
        dictionary['app_name'] = app_name
    except Exception as e:
        return JsonResponse({'Exception': str(e)})
    else:
        return render(request, 'single_app/profiling.html', dictionary)


def services_json(request, app_name):
    """ Generate the content for service_component.html
    """
    services = mu.get_services(app_name)
    # make format like this http://sunsp.net/code/main_bubble_json.html
    services_json = {'name': 'bubble',
                     'children': [
                         {'name': app_name,
                             'description': 'some description here', 'children': []}
                     ]}
    for service in services:
        services_json['children'][0]['children'].append({'name': service})

    return JsonResponse(services_json)


def calibration_json(request, app_name):

    return JsonResponse({})


def profiling_json(request, app_name):
    return JsonResponse({})


def dummyJson():
    return {'field_a': 123, 'field_b': {'field_c': [[1, 2, 3], [5, 5, 2]]}}
