# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import JsonResponse


def update(request):
    return JsonResponse({'Status': 'OK'})
