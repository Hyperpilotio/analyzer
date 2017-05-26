# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from models import dummy_model


@csrf_exempt
def testid2feature(request):
    if request.method == 'POST':
        try:
            test_id = json.loads(request.body)['test_id']
        except Exception as e:
            response = HttpResponse(e)
        else:
            response = JsonResponse(dummy_model(test_id))
    else:
        response = HttpResponse(
            "unsupported method: {}".format(request.method))

    return response
