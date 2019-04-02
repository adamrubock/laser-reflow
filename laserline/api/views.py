from .models import Recipe, TimePoint
from .serializers import TimePointSerializer, RecipeSerializer
from rest_framework.viewsets import GenericViewSet
from rest_framework import mixins


class RecipeViewSet(mixins.CreateModelMixin, mixins.DestroyModelMixin,
                    mixins.ListModelMixin, mixins.RetrieveModelMixin,
                    mixins.UpdateModelMixin, GenericViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
