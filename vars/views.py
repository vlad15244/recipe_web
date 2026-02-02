from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.template import loader
from django.http import HttpResponse
from django.conf import settings
from django.views.generic.list import ListView
from django.utils import timezone

from .models import Recipe, Trends, Message
from .forms import RecipeForm, LoginForm
from datetime import datetime, date
from .convert import convert_buffer
from xhtml2pdf import pisa 

def index(request):
    template = loader.get_template('vars/index.html')
    recipes = Recipe.objects.order_by('-created_at')
    context = {'recipes': recipes}
    return HttpResponse(template.render(context, request))
# Create your views here.

def opcua_realtime(request):
    return render(request, 'vars/realtime.html')


class TrendsCurrentMonth(ListView):
    model = Trends
    template_name = 'vars/trends_month.html'
    context_object_name = 'trends_month'

    def get_queryset(self):
        now = timezone.now()
        
        return Trends.objects.filter(
                                    timestamp__month = now.month, timestamp__year = now.year)
    
    
    def get_context_data(self, **kwargs):
        self.query_set = self.get_queryset()

        trends = convert_buffer(self.query_set)
        
        context = {
            'trends_month': trends,
            'has_data': len(trends) > 0  # флаг наличия данных
        }
        return context

class MessageCurrentMonth(ListView):
    model = Message
    template_name = 'vars/message_month.html'
    context_object_name = 'message_month'

    def get_queryset(self):
        now = timezone.now()
        
        return Message.objects.filter(
                                    timestamp__month = now.month, timestamp__year = now.year)
    
    
    def get_context_data(self, **kwargs):
        self.query_set = self.get_queryset()

        messages = self.query_set
        
        context = {
            'messages': messages,
            'has_data': len(messages) > 0  # флаг наличия данных
        }
        return context


def add_recipe(request):
    if request.method == 'POST':
        form = RecipeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('recipe_list')
    else:
        form = RecipeForm()
    
    return render(request, 'vars/add_recipe.html', {'form':form})

def trends(request):

    date_str = request.GET.get('start_date')
    trends = convert_buffer(Trends.objects.all())

    buffer = []
    for trend in trends:
        buffer.append(trend)
        
    if date_str:
        try:
            date_time = datetime.strptime(date_str, '%Y-%m-%d').date()

            trends = convert_buffer(Trends.objects.filter(
                                            timestamp__date = date_time))

        except ValueError:
            pass
            
    context = {
        'trends': trends,
        'selected_date': date_str,
        'has_data': len(trends) > 0  # флаг наличия данных
    }

    template = loader.get_template('vars/trends.html')
    return HttpResponse(template.render(context, request)) 




def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(request, username=cd['username'], password=cd['password'])
            
            # Проверка user теперь ВНУТРИ блока is_valid()
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect('realtime')
            else:
                pass
    else:
        form = LoginForm()    

    return render(request, 'vars/login.html', {'form': form})  

def trends_pdf(request):
    # Получаем дату из GET-параметра
    date_str = request.GET.get('start_date')

    if date_str:
        try:
            date_time = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            date_time = None #Если ошибка, просто скажем сегодня
    else:
        date_time = date.today()

    # Фильтруем данные
    if date_time:
        trends_queryset = Trends.objects.filter(timestamp__date=date_time)
    else:
        trends_queryset = Trends.objects.all()

    trends_list = list(trends_queryset)
    trends = convert_buffer(trends_list)


    # Подготавливаем контекст для шаблона PDF
    context = {
        'base_dir': settings.BASE_DIR,  # Передаем путь к проекту
        'trends': trends,
        'selected_date': date_str or 'Все данные',
        'has_data': len(trends) > 0
    }

    # Загружаем шаблон для PDF
    template = loader.get_template('vars/trends_pdf.html')
    html = template.render(context)


    # Генерируем PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="trends_{date_str or "all"}.pdf"'

    pisa_status = pisa.CreatePDF(
        html, dest=response, encoding='utf-8'
    )

    if pisa_status.err:
        return HttpResponse('Error generating PDF', status=400)
    return response


def message(request):
    date_str = request.GET.get('start_date')
    messages = Message.objects.all()

    if date_str:
        try:
            date_time = datetime.strptime(date_str, '%Y-%m-%d').date()

            messages = Message.objects.filter(
                                            timestamp__date = date_time)

        except ValueError:
            pass
            
    context = {
        'messages': messages,
        'selected_date': date_str,
        'has_data': len(messages) > 0  # флаг наличия данных
    }
    print(messages)
    template = loader.get_template('vars/message.html')
    return HttpResponse(template.render(context, request)) 
