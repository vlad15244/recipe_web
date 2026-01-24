from django import forms
from .models import Recipe

class RecipeForm(forms.ModelForm):

    name = forms.CharField(label="Наименование")
    var1 = forms.FloatField(label="Параметр - 1")
    var2 = forms.IntegerField(label="Параметр - 2")  
    var3 = forms.BooleanField(label="Параметр - 3")  

    class Meta:
        model = Recipe
        fields = '__all__'

class LoginForm(forms.Form):
    username = forms.CharField(label="Пользователь")
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")