from django.shortcuts import render
from django.template import loader
from django.http import HttpResponse

from .models import Recipe


def index(request):
    template = loader.get_template('vars/index.html')
    recipes = Recipe.objects.order_by('-created_at')
    context = {'recipes': recipes}
    return HttpResponse(template.render(context, request))
# Create your views here.
