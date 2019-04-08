
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from redis import Redis

# imports from this project
from api.models import Recipe, TimePoint
from api.serializers import RecipeSerializer
from .serializers import LaserlineWriteSerializer


class LaserlineInterface(APIView):
    def post(self, request):
        serializer = LaserlineWriteSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            r = Redis(password='laserr3flow')
            pipe = r.pipeline()
            # digital outputs are negations of the values we set them to.
            # web interface shouldn't have to deal with this counterintuitive nature
            pipe.setbit('digital_outputs', 0,
                        not serializer.data.get('threshold_digital'))
            pipe.setbit('digital_outputs', 1,
                        not serializer.data.get('shutter_digital'))
            pipe.setbit('digital_outputs', 2,
                        not serializer.data.get('alignment_laser_digital'))
            pipe.setbit('digital_outputs', 3,
                        not serializer.data.get('reset_error_digital'))
            pipe.set('x_dim_analog', serializer.data.get('x_width'))
            pipe.set('y_dim_analog', serializer.data.get('y_width'))
            pipe.execute()

            running = r.exists('run_active')
            run_request = serializer.data.get('run_request')
            if run_request == 'DO_NOTHING':
                return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
            else if run_request == 'START':
                if running:
                    return Response(serializer.data, status=status.HTTP_409_CONFLICT)
                else:
                    # TODO make sure these are correct position and polarity
                    ok_to_start = (r.getbit('digital_inputs', 2)
                                   or r.getbit('digital_inputs', 3)
                                   or not r.getbit('digital_inputs', 4)
                                   or not r.getbit('digital_inputs', 5)
                                   or not r.getbit('digital_inputs', 6))
                    if ok_to_start:
                        r.delete('durations', 'levels')
                        rs = RecipeSerializer(serializer.data.get('recipe'))
                        timepoints = rs.data.get('timepoints')
                        r.lpush('durations', [
                                i.get('timepoint_duration') for i in timepoints])
                        r.lpush('levels', [i.get('power_level')
                                           for i in timepoints])
                        r.set('x_axis', rs.data.get('x_width'))
                        r.set('y_axis', rs.data.get('y_width'))
                        r.set('start_run', '')
                    else:
                        return Response(serializer.data, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            else:
                # run_request must be 'CANCEL'
                if running:
                    r.set('cancel_run', '')
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
