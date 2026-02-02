from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from farminsight_dashboard_backend.models import EnergySource
from farminsight_dashboard_backend.serializers.energy_source_serializer import EnergySourceSerializer
from farminsight_dashboard_backend.services import is_member, is_admin, get_organization_by_fpf_id
from farminsight_dashboard_backend.services.energy_source_services import (
    get_energy_source_by_id,
    get_energy_sources_by_fpf_id,
    create_energy_source,
    update_energy_source,
    delete_energy_source,
    get_total_available_power_by_fpf_id,
    get_current_power_output_by_fpf_id
)
from farminsight_dashboard_backend.utils import get_logger


logger = get_logger()


class EnergySourceView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, source_id):
        """
        Get an energy source by its id
        """
        source = get_energy_source_by_id(source_id)
        return Response(
            EnergySourceSerializer(source).data,
            status=status.HTTP_200_OK
        )

    def put(self, request, source_id):
        """
        Update an energy source by given id
        """
        source = get_energy_source_by_id(source_id)

        if not is_member(request.user, get_organization_by_fpf_id(str(source.FPF.id))):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = update_energy_source(source_id, request.data)
        logger.info("Energy source updated successfully", extra={'resource_id': source_id})

        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, source_id):
        """
        Delete an energy source by given id
        """
        source = get_energy_source_by_id(source_id)

        if not is_admin(request.user, get_organization_by_fpf_id(str(source.FPF.id))):
            return Response(status=status.HTTP_403_FORBIDDEN)

        delete_energy_source(source)
        logger.info("Energy source deleted successfully", extra={'resource_id': source_id})

        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_energy_source(request):
    """
    Create a new energy source
    """
    fpf_id = request.data.get('fpfId')
    if not fpf_id:
        return Response({"error": "Missing fpfId"}, status=status.HTTP_400_BAD_REQUEST)

    if not is_member(request.user, get_organization_by_fpf_id(fpf_id)):
        return Response(status=status.HTTP_403_FORBIDDEN)

    try:
        source = create_energy_source(fpf_id, request.data)
        logger.info(f"Energy source '{source.name}' created successfully")

        return Response(
            EnergySourceSerializer(source).data,
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        logger.error(f"Error creating energy source: {e}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_energy_sources_by_fpf(request, fpf_id: str):
    """
    Get all energy sources for an FPF
    """
    sources = get_energy_sources_by_fpf_id(fpf_id)
    total_available = get_total_available_power_by_fpf_id(fpf_id)
    current_output = get_current_power_output_by_fpf_id(fpf_id)

    return Response({
        "sources": EnergySourceSerializer(sources, many=True).data,
        "total_available_watts": total_available,
        "current_output_watts": current_output
    }, status=status.HTTP_200_OK)
