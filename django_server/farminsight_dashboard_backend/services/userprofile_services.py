import secrets
import string
from django.db.models import QuerySet, Q

from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import Userprofile


def search_userprofiles(search_string) -> QuerySet[Userprofile]:
    return Userprofile.objects.filter(Q(name__contains=search_string) | Q(email__contains=search_string)).all()


def update_userprofile_name(userprofile_id, new_name):
    """
    Updates the name of the userprofile
    :param userprofile_id:
    :param new_name:
    :return:
    """
    try:
        user_profile = Userprofile.objects.get(id=userprofile_id)
        user_profile.name = new_name
        user_profile.save()
        return user_profile
    except Userprofile.DoesNotExist:
        raise NotFoundException(f'Userprofile {userprofile_id} not found.')


def set_password_to_random_password(userprofile_id: str) -> string:
    """
    This is a (hopefully temporary) measure for a sysadmin to forcefully change a users password should they forget it
    and manually (safely) hand it over to said user.
    This should be removed as soon as we can send out email for a "forgot password" feature
    """
    user_profile = Userprofile.objects.get(id=userprofile_id)
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for i in range(10))
    user_profile.set_password(password)
    return password
