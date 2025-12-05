from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from farminsight_dashboard_backend.models import EnergyConsumer
from farminsight_dashboard_backend.serializers.energy_consumer_serializer import (
    EnergyConsumerSerializer,
    EnergyConsumerDetailSerializer
)
from farminsight_dashboard_backend.services import is_member, is_admin, get_organization_by_fpf_id
from farminsight_dashboard_backend.services.energy_consumer_services import (
    get_energy_consumer_by_id,
    get_energy_consumers_by_fpf_id,
    create_energy_consumer,
    update_energy_consumer,
    delete_energy_consumer,
    get_total_consumption_by_fpf_id
)
from farminsight_dashboard_backend.utils import get_logger


logger = get_logger()


class EnergyConsumerView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, consumer_id):
        """
        Get an energy consumer by its id
        """
        consumer = get_energy_consumer_by_id(consumer_id)
        return Response(
            EnergyConsumerDetailSerializer(consumer).data,
            status=status.HTTP_200_OK
        )

    def put(self, request, consumer_id):
        """
        Update an energy consumer by given id
        """
        consumer = get_energy_consumer_by_id(consumer_id)

        if not is_member(request.user, get_organization_by_fpf_id(str(consumer.FPF.id))):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = update_energy_consumer(consumer_id, request.data)
        logger.info("Energy consumer updated successfully", extra={'resource_id': consumer_id})

        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, consumer_id):
        """
        Delete an energy consumer by given id
        """
        consumer = get_energy_consumer_by_id(consumer_id)

        if not is_admin(request.user, get_organization_by_fpf_id(str(consumer.FPF.id))):
            return Response(status=status.HTTP_403_FORBIDDEN)

        delete_energy_consumer(consumer)
        logger.info("Energy consumer deleted successfully", extra={'resource_id': consumer_id})

        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_energy_consumer(request):
    """
    Create a new energy consumer
    """
    fpf_id = request.data.get('fpfId')
    if not fpf_id:
        return Response({"error": "Missing fpfId"}, status=status.HTTP_400_BAD_REQUEST)

    if not is_member(request.user, get_organization_by_fpf_id(fpf_id)):
        return Response(status=status.HTTP_403_FORBIDDEN)

    try:
        consumer = create_energy_consumer(fpf_id, request.data)
        logger.info(f"Energy consumer '{consumer.name}' created successfully")

        return Response(
            EnergyConsumerSerializer(consumer).data,
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        logger.error(f"Error creating energy consumer: {e}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_energy_consumers_by_fpf(request, fpf_id: str):
    """
    Get all energy consumers for an FPF
    """
    consumers = get_energy_consumers_by_fpf_id(fpf_id)
    total_consumption = get_total_consumption_by_fpf_id(fpf_id)

    return Response({
        "consumers": EnergyConsumerDetailSerializer(consumers, many=True).data,
        "total_consumption_watts": total_consumption
    }, status=status.HTTP_200_OK)
