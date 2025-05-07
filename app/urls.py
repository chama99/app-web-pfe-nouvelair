from django.urls import path
from .views import upload_csv_view , CustomLoginView 
from django.contrib.auth.decorators import login_required

urlpatterns = [
     path('',CustomLoginView.as_view(), name='login'),
     path('upload/',upload_csv_view, name='upload_csv'),
     

]
