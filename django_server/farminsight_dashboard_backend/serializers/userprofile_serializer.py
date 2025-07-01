from rest_framework import serializers
from farminsight_dashboard_backend.models import Userprofile


class UserprofileSerializer(serializers.ModelSerializer):
    isActive = serializers.BooleanField(read_only=True, source='is_active')

    class Meta:
        model = Userprofile
        read_only_fields = ('id', 'systemRole')
        fields = ('id', 'name', 'email', 'systemRole', 'isActive')

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)