'''
from django.db import models
from django.core.exceptions import ValidationError
from api.models import Recipe

class RecipeRun(models.Model):
    is_active = models.BooleanField(default=False)
    recipe = models.OneToOneField(Recipe,on_delete=models.DO_NOTHING)
    job_id = models.CharField(max_length=256)

    def save(self, *args, **kwargs):
        if RecipeRun.objects.exists() and not self.pk:
            raise ValidationError('There can be only one instance')
        return super(RecipeRun, self).save(*args, **kwargs)    
'''