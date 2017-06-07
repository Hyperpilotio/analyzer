# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.http import JsonResponse
from django.shortcuts import render
import core.mongo_util as mu


def show(request, app_name):
    """ Load data from mongoDB and construct json objects.
    Args:
        app_name(str): The 'appName' in database.
    """
    try:
        apps = set(mu.get_available_apps(collection='profiling'))

        services = mu.get_services(app_name)
        services_json = {'num_service': len(
            services), 'servies_name': services}

        # what information to be sent?
        calibration_json = {}
        calibration_document = mu.get_calibration_document(app_name)
        calibration_json['x_axis'] = [i['loadIntensity']
                                      for i in calibration_document['testResult']]
        calibration_json['y_axis'] = [[i['throughput']
                                       for i in calibration_document['testResult']]]
        calibration_json['y_axis'].append(
            [i['latency'] for i in calibration_document['testResult']])

        profiling_json = mu.create_profiling_dataframe(app_name).to_json()

    except Exception as e:
        return JsonResponse({'Exception': str(e)})
    else:
        return render(request, 'single_app/single_app.html',
                      {'apps': apps,
                       'app_name': app_name,
                       'json': {
                           'services': services_json,
                           'calibration': calibration_json,
                           'profiling': profiling_json}})


def dummyJson():
    return {'field_a': 123, 'field_b': {'field_c': [[1, 2, 3], [5, 5, 2]]}}
