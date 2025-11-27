import secrets
import string
from django.db.models import QuerySet, Q
from oauth2_provider.models import AccessToken, RefreshToken, IDToken

from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import Userprofile
from farminsight_dashboard_backend.serializers import UserprofileSerializer
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()


def search_userprofiles(search_string) -> QuerySet[Userprofile]:
    logger.debug(f"Searching for user profiles with query: '{search_string}'.")
    return Userprofile.objects.filter(Q(name__contains=search_string) | Q(email__contains=search_string)).all()


def update_userprofile_name(userprofile_id, new_name):
    """
    Updates the name of the userprofile
    :param userprofile_id:
    :param new_name:
    :return:
    """
    logger.debug(f"Attempting to update name for user profile.")
    try:
        user_profile = Userprofile.objects.get(id=userprofile_id)
        old_name = user_profile.name
        user_profile.name = new_name
        user_profile.save()
        logger.info(f"Updated name for user '{old_name}' to '{new_name}'.")
        return user_profile
    except Userprofile.DoesNotExist:
        logger.warning(f"User profile not found.")
        raise NotFoundException(f'Userprofile not found.')


def set_password_to_random_password(userprofile_id: str) -> string:
    """
    This is a (hopefully temporary) measure for a sysadmin to forcefully change a users password should they forget it
    and manually (safely) hand it over to said user.
    This should be removed as soon as we can send out email for a "forgot password" feature
    """
    logger.debug(f"Attempting to set a random password for user profile.")
    try:
        user_profile = Userprofile.objects.get(id=userprofile_id)
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for i in range(10))
        user_profile.set_password(password)
        user_profile.save()
        logger.info(f"Successfully set a new random password for user '{user_profile.name}'.")
        return password
    except Userprofile.DoesNotExist:
        logger.error(f"User profile not found when trying to set a random password.")
        raise


def all_userprofiles() -> UserprofileSerializer:
    logger.debug("Fetching all user profiles.")
    return UserprofileSerializer(Userprofile.objects.all(), many=True)


def set_active_status(user_profile_id: str, active: bool) -> UserprofileSerializer:
    logger.debug(f"Attempting to set active status to '{active}' for user profile.")
    try:
        user_profile = Userprofile.objects.get(id=user_profile_id)
        user_profile.is_active = active
        user_profile.save()
        logger.info(f"Set active status for user '{user_profile.name}' to '{active}'.")

        if not active:
            logger.debug(f"User '{user_profile.name}' is inactive, removing their access tokens.")
            AccessToken.objects.filter(user_id=user_profile_id).delete()
            RefreshToken.objects.filter(user_id=user_profile_id).delete()
            IDToken.objects.filter(user_id=user_profile_id).delete()
            logger.info(f"Removed all access tokens for user '{user_profile.name}'.")

        return UserprofileSerializer(user_profile)
    except Userprofile.DoesNotExist:
        logger.error(f"User profile not found when trying to set active status.")
        raise
