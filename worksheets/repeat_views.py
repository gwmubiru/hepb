from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from .models import Sample

class plasmaListJson(APIView):  # Renamed to match convention (camelCase)
    renderer_classes = [JSONRenderer]

    def get(self, request):
        # Extract DataTables parameters
        draw = int(request.query_params.get('draw', 1))
        start = int(request.query_params.get('start', 0))
        length = int(request.query_params.get('length', 10))
        search_value = request.query_params.get('search[value]', None)
        order_column = request.query_params.get('order[0][column]', None)
        order_dir = request.query_params.get('order[0][dir]', None)

        # Map order_column index to field names
        column_mapping = {
            '0': 'barcode',
            '1': 'facility_reference',
        }
        order_field = column_mapping.get(order_column, 'barcode')  # Default to 'barcode'

        # Determine ordering direction
        if order_dir == 'desc':
            order_field = '-' + order_field

        # Filter samples (stage=4, sample_type='P')
        samples = Sample.objects.filter(stage=4, sample_type='P')

        # Apply search filter if provided
        if search_value:
            samples = samples.filter(barcode__icontains=search_value)

        # Order samples
        samples = samples.order_by(order_field)

        # Get total counts
        recordsTotal = Sample.objects.filter(stage=4, sample_type='P').count()
        recordsFiltered = samples.count() if search_value else recordsTotal

        # Get paginated data
        data = []
        for sample in samples[start:start + length]:
            row = [str(sample.id), sample.barcode, sample.facility_reference]
            data.append(row)

        # Prepare full DataTables response
        response = {
            'draw': draw,
            'recordsTotal': recordsTotal,
            'recordsFiltered': recordsFiltered,
            'data': data,
        }

        # Return the full response
        return Response(response)