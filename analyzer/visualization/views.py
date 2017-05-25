# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from models import dummy_visualizer


@csrf_exempt
def visualize(request):
    if request.method == 'POST':
        try:
            json_data = json.loads(request.body)
        except Exception as e:
            response = HttpResponse(e)
        else:
            response = JsonResponse(dummy_visualizer())
    else:
        response = HttpResponse(
            "unsupported method: {}".format(request.method))

    return response