from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Recipe(models.Model):
	recipe_name = models.CharField(max_length=100,unique=True)
	x_width = models.FloatField(validators=[MinValueValidator(0.0),MaxValueValidator(1.0)])
	y_width = models.FloatField(validators=[MinValueValidator(0.0),MaxValueValidator(1.0)])

	def __str__(self):
		return self.recipe_name

class TimePoint(models.Model):
	timepoint_duration = models.IntegerField(validators=[MinValueValidator(1),MaxValueValidator(600000)])
	power_level = models.FloatField(validators=[MinValueValidator(0.0),MaxValueValidator(1.0)])
	recipe = models.ForeignKey(Recipe,on_delete=models.CASCADE,related_name='timepoints')