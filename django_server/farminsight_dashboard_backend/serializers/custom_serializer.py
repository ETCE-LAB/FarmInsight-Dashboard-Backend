from rest_framework import serializers


class CustomSerializer(serializers.ModelSerializer):
    '''
    this serializer collects all errors and reports them at once, which is preferable for input form validation,
    but otherwise not required
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_validated = False

    def is_valid(self, *, raise_exception=True):
        super().is_valid(raise_exception=False)

        if self._errors and not self.is_validated:
            try:
                self.validate(self.data)
            except serializers.ValidationError as e:
                self._errors['non_field_errors'] = e.detail

        if self._errors and raise_exception:
            raise serializers.ValidationError(self._errors)

        return not bool(self._errors)
