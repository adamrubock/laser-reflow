
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from redis import Redis

# imports from this project
from api.models import Recipe, TimePoint
from api.serializers import RecipeSerializer

class SubmitRun(APIView):
	def get(self, request):

		#The URL syntax will  be /execute/<recipe id number>

		try:
			url_id = self.kwargs.get("url_id")
		except Exception:
			return Response({'errormsg': 'The request URL is not formed properly.'},status.HTTP_400_BAD_REQUEST)
		try:
			recipe = Recipe.objects.get(id=url_id)
		except Exception:
			return Response({'errormsg': 'The requested recipe ID was not found or invalid.'},status.HTTP_404_NOT_FOUND)

		r = Redis(password='laserr3flow')
		if r.exists('run_active'):
			return Response({'errormsg': 'A run is already underway.'},status.HTTP_409_CONFLICT)
		
		timepoints = RecipeSerializer(recipe.data.get('timepoints'))

		# check shutter is open
		# check threshold is on
		# check interlocks closed
		# check no error signal
		

		return Response(status=status.HTTP_202_ACCEPTED)

class RunStatus(APIView):
	def get(self,request):
		r = StrictRedis(password='laserr3flow')
		pass
