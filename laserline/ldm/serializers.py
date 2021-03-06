from api.models import Recipe
from rest_framework import serializers


class LaserlineWriteSerializer(serializers.Serializer):
    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all(), required=False)

    RUN_REQUEST_CHOICES = (
        ('DO_NOTHING', 'Do Nothing'),
        ('START', 'Start'),
        ('CANCEL', 'Cancel'))
    run_request = serializers.ChoiceField(
        RUN_REQUEST_CHOICES, default='DO_NOTHING')

    x_width = serializers.FloatField(min_value=0.0, max_value=1.0, required=False)
    y_width = serializers.FloatField(min_value=0.0, max_value=1.0, required=False)

    threshold_digital = serializers.BooleanField(required=False)
    shutter_digital = serializers.BooleanField(required=False)
    alignment_laser_digital = serializers.BooleanField(required=False)
    reset_error_digital = serializers.BooleanField(required=False)
