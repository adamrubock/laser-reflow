from rest_framework import serializers
from .models import TimePoint, Recipe

class TimePointSerializer(serializers.ModelSerializer):
	class Meta:
		model = TimePoint
		fields=('id','timepoint_duration','power_level')

class RecipeSerializer(serializers.ModelSerializer):
	timepoints = TimePointSerializer(many=True)

	class Meta:
		model = Recipe
		fields=('id','recipe_name','x_width','y_width','timepoints')

	def create(self, validated_data):
		new_recipe = Recipe()
		new_recipe.recipe_name = validated_data.get('recipe_name')
		new_recipe.x_width = validated_data.get('x_width')
		new_recipe.y_width = validated_data.get('y_width')
		new_recipe.save()
		
		recipe_timepoints = validated_data.get('timepoints')
		bulk_timepoints = []
		for timepoint in recipe_timepoints:
			new_timepoint = TimePoint(recipe=new_recipe,**timepoint)
			bulk_timepoints.append(new_timepoint)

		TimePoint.objects.bulk_create(bulk_timepoints)
		return new_recipe
	
	def update(self,instance,validated_data):
		instance.recipe_name=validated_data.get('recipe_name')
		instance.x_width=validated_data.get('x_width')
		instance.y_width=validated_data.get('y_width')
		instance.save()
		TimePoint.objects.filter(recipe=instance).delete()
		recipe_timepoints = validated_data.get('timepoints')
		bulk_timepoints = []
		for timepoint in recipe_timepoints:
			new_timepoint = TimePoint(recipe=instance,**timepoint)
			bulk_timepoints.append(new_timepoint)
		
		TimePoint.objects.bulk_create(bulk_timepoints)
		return instance
	


