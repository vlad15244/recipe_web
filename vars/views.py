from django.shortcuts import render, redirect
from django.template import loader
from django.http import HttpResponse

from .models import Recipe
from .forms import RecipeForm

def index(request):
    template = loader.get_template('vars/index.html')
    recipes = Recipe.objects.order_by('-created_at')
    context = {'recipes': recipes}
    return HttpResponse(template.render(context, request))
# Create your views here.


def add_recipe(request):
    if request.method == 'POST':
        form = RecipeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('recipe_list')
    else:
        form = RecipeForm()
    
    return render(request, 'vars/add_recipe.html', {'form':form})