'''
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from redis import StrictRedis
import redis_lock
import django_rq
##from rq import 
# imports from this project
from api.models import Recipe, TimePoint
from api.serializers import RecipeSerializer
from daemon.runrecipe import run

class SubmitRun(APIView):
	def get(self, request):

		#The URL syntax will simply be /execute/<recipe id number>
		#first check if already locked
		#otherwise, aquire lock and pass the lock when checks are done, unlock it if it fails

		try:
			url_id = self.kwargs.get("url_id")
		except Exception:
			return Response({'errormsg': 'The request URL is not formed properly.'},status.HTTP_400_BAD_REQUEST)

		try:
			recipe = Recipe.objects.get(id=url_id)
		except Exception:
			return Response({'errormsg': 'The requested recipe ID was not found or invalid.'},status.HTTP_404_NOT_FOUND)

		r = StrictRedis(password='laserr3flow')
		lock = redis_lock.Lock(r,"execute_lock")
		if not lock.acquire(blocking=False):
			return Response({'errormsg': 'A run is already underway.'},status.HTTP_409_CONFLICT)
		
		timepoints = RecipeSerializer(Recipe.objects.get(recipe).data.get('timepoints'))
		# TODO implement the real McCoy
		# now run series of checks, use try/except blocks here:
		# check shutter is open
		# check threshold is on
		# check interlocks closed
		# check no error signal

		django_rq.enqueue(run,timepoints,lock)
		django_rq.get_worker().work(burst=True)
		return Response(status=status.HTTP_202_ACCEPTED)

class RunStatus(APIView):
	def get(self,request):
		r = StrictRedis(password='laserr3flow')
		lock = redis_lock.Lock(r,"execute_lock")
		if not lock.acquire(blocking=False):
			return Response({'running': True})
		else:
			lock.release()
			return Response({'running': False})

class CancelRun(APIView):
	def get(self,request):
		r = StrictRedis(password='laserr3flow')
		default_queue = django_rq.queues.get_queue(connection=r)
		for j in django_rq.workers.Worker.all(connection=r,queue=default_queue):
			j.kill_horse()
		# TODO turn laser off here
		lock = redis_lock.Lock(r,"execute_lock")
		lock.reset()
		return Response(data={'killed': True})
'''