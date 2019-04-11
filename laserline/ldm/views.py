
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from redis import Redis
import logging

# imports from this project
from api.models import Recipe, TimePoint
from api.serializers import RecipeSerializer
from .serializers import LaserlineWriteSerializer


@api_view(['POST'])
def control(request):
    serializer = LaserlineWriteSerializer(data=request.data, partial=True)
    if serializer.is_valid():
        r = Redis(password='laserr3flow')
        pipe = r.pipeline()
        # digital outputs are negations of the values we set them to.
        # web interface shouldn't have to deal with this counterintuitive nature
        if serializer.validated_data.get('threshold_digital') is not None:
            pipe.setbit('digital_outputs', 0,
                        not serializer.validated_data.get('threshold_digital'))

        if serializer.validated_data.get('shutter_digital') is not None:
            pipe.setbit('digital_outputs', 1,
                        not serializer.validated_data.get('shutter_digital'))

        if serializer.validated_data.get('alignment_laser_digital') is not None:
            pipe.setbit('digital_outputs', 2,
                        not serializer.validated_data.get('alignment_laser_digital'))

        if serializer.validated_data.get('reset_error_digital') is not None:
            pipe.setbit('digital_outputs', 3,
                        not serializer.data.get('reset_error_digital'))

        if serializer.validated_data.get('x_width') is not None:
            pipe.hmset('analog_outputs', {
                'x_dim_analog': serializer.validated_data.get('x_width')})
        
        if serializer.validated_data.get('y_width') is not None:
            pipe.hmset('analog_outputs', {
                'y_dim_analog': serializer.validated_data.get('y_width')})

        pipe.execute()

        running=r.exists('run_active')
        run_request=serializer.validated_data.get('run_request')
        if run_request is not None:
            if run_request == 'DO_NOTHING':
                return Response(serializer.data, status = status.HTTP_202_ACCEPTED)
            elif run_request == 'START':
                if serializer.validated_data.get('recipe') is None:
                    return Response({'error': 'no recipe'},status=status.HTTP_400_BAD_REQUEST)
                if running:
                    return Response({'error': 'already running'}, status = status.HTTP_409_CONFLICT)
                else:
                    # TODO make sure these are correct position and polarity
                    ok_to_start=True
                                # (r.getbit('digital_inputs', 2)
                                #    or r.getbit('digital_inputs', 3)
                                #    or not r.getbit('digital_inputs', 4)
                                #    or not r.getbit('digital_inputs', 5)
                                #    or not r.getbit('digital_inputs', 6))
                    if ok_to_start:
                        r.delete('durations', 'levels')
                        rs=RecipeSerializer(
                            serializer.validated_data.get('recipe'))
                        timepoints = rs.data.get('timepoints')
                        r.lpush('durations', *(
                                i.get('timepoint_duration') for i in timepoints))
                        r.lpush('levels', *(i.get('power_level')
                                            for i in timepoints))
                        r.set('x_axis', rs.data.get('x_width'))
                        r.set('y_axis', rs.data.get('y_width'))
                        r.set('start_run', '')
                    else:
                        return Response({'error': 'cannot start'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            else:
                # run_request must be 'CANCEL'
                if running:
                    r.set('cancel_run', '')
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response({'error': 'not running'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data, status = status.HTTP_200_OK)
    return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

digital_input_names = (
    'sleep_mode_digital',
    'warning_digital',
    'cable_error_digital',
    'collective_error_digital',
    'safety_circuit_digital',
    'shutter_open_digital',
    'threshold_digital',
    'laser_on_digital',
    'shutter_closed_digital',
)

@api_view(['GET'])
def info(request):
    r = Redis(password='laserr3flow')
    response ={}# {name: float(val) for name, val in r.hgetall('analog_inputs').items()}
    # now the digital inputs
    # TODO parameterize
    #response.update(dict(zip(digital_input_names,
     #   (r.getbit('digital_inputs',i) for i in range(9)))))
    response.update({'run_active': r.exists('run_active')})
    return Response(response,status=status.HTTP_200_OK)

    
