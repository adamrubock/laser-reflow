'''
from rest_framework import serializers
from .models import RecipeRun
from api.models import Recipe

class RecipeRunSerializer(serializers.ModelSerializer):
	class Meta:
		model = Recipe
		fields = '__all__'		
'''