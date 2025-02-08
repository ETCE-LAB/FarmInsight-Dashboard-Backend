from rest_framework import serializers

class DateRangeSerializer(serializers.Serializer):
    """
    Accepts format of ISO 8601 (%Y-%m-%dT%H:%M:%SZ) and a simpler YYYY-MM-DD format.
    """
    from_date = serializers.DateTimeField(
        input_formats=['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d'],
        required=True,
        error_messages = {
            'required': "The 'from' query parameter is required.",
            'invalid': "Invalid date format for 'from'. Expected YYYY-MM-DD or ISO 8601."
        }
    )

    to_date = serializers.DateTimeField(
        input_formats=['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d'],
        required=False,
        default=None,
        error_messages={
            'invalid': "Invalid date format for 'to'. Expected YYYY-MM-DD or ISO 8601."
        }
    )

    def validate(self, data):
        """
        Check that ``from`` parameter is given and that it is before the ``to`` parameter
        :param data:
        :return:
        """
        from_date = data.get('from_date')
        to_date = data.get('to_date')

        if from_date is None:
            raise serializers.ValidationError({"from": "The 'from' query parameter is required."})


        if to_date and to_date < from_date:
            raise serializers.ValidationError({"to": "'to' date must be later than 'from' date."})

        return data

    def to_internal_value(self, data):
        """
        Override to map 'from' and 'to' in input data to 'from_date' and 'to_date'.
        """
        data = data.copy()

        if 'from' in data:
            data['from_date'] = data.pop('from')[0]
        if 'to' in data:
            data['to_date'] = data.pop('to')[0]

        return super().to_internal_value(data)
