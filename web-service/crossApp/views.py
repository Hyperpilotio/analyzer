# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from models import LinearRegression1


@csrf_exempt
def predict(request):
    if request.method == 'POST':
        requestBody = json.loads(request.body)
        app1, app2 = requestBody['app1'], requestBody['app2']
        model = requestBody['model']
        collection = requestBody[
            'collection'] if 'collection' in requestBody else None

        if model == 'LinearRegression1':
            response = JsonResponse(
                LinearRegression1(numDims=3).fit(None, None).predict(app1, app2, collection).to_dict())
        else:
            response = JsonResponse(
                {'Exception': "Unimplemented model: {}".format(model)}, status=501)
    else:
        response = JsonResponse({'Exception':
                                 "Unsupported method: {}".format(request.method)}, status=501)

    return response
