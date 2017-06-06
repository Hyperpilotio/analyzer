# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render


def show(request, app_name):

    return render(request, 'single_app/single_app.html',
                  {'app_name': app_name,
                   'json': {
                       'services': dummyJson(),
                       'calibration': dummyJson(),
                       'profiling': dummyJson()}})


def dummyJson():
    return {'field_a': 123, 'field_b': {'field_c': [[1, 2, 3], [5, 5, 2]]}}
