#from django.shortcuts import render
from .models import Recipe, TimePoint
from .serializers import TimePointSerializer, RecipeSerializer
#from django.http import Http404
from rest_framework.viewsets import GenericViewSet
#from rest_framework.response import Response
from rest_framework import mixins#status, mixins

class RecipeViewSet(
		mixins.CreateModelMixin,
		mixins.DestroyModelMixin,
		mixins.ListModelMixin,
		mixins.RetrieveModelMixin,
		mixins.UpdateModelMixin,
		GenericViewSet):
	queryset = Recipe.objects.all()
	serializer_class = RecipeSerializer
	
	

