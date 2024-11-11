from apps.settings.models import TaxSettings

def tax_method(request):
    """Returns all tax methods."""
    # if request.user.id != None:
    #     return TaxSettings.objects.all()
    pass