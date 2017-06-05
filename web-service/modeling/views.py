# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from models import LinearRegression1


@csrf_exempt
def predict_app2app(request):
    if request.method == 'POST':
        try:
            request_body = json.loads(request.body)
            model, app_1, app_2 = request_body[
                'model'], request_body['app_1'], request_body['app_2']

            if model == 'LinearRegression1':
                response = JsonResponse(
                    LinearRegression1(num_dims=3).fit(None, None).predict(app_1, app_2).to_dict())
            else:
                response = JsonResponse(
                    {'Exception': "Unimplemented model: {}".format(model)}, status=501)
        except Exception as e:
            response = JsonResponse({'Exception': str(e)}, status=500)

    else:
        response = JsonResponse({'Exception':
                                 "Unsupported method: {}".format(request.method)}, status=501)

    return response
