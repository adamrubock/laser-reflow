from .views import control, info
from django.urls import path

urlpatterns = [
	path('control', control),
	path('info', info),
]