from django.shortcuts import render

# Create your views here.
from restapi.models import Lead
from restapi.serializers import LeadSerializer
from rest_framework import generics

class LeadListCreate(generics.ListCreateAPIView):
	queryset = Lead.objects.all()
	serializer_class = LeadSerializer