from django.urls import path

from .views import index, add_recipe

urlpatterns = [
    path('', index, name='recipe_list'),
    path('new/', add_recipe, name='add_new')
]