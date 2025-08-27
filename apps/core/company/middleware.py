from django.shortcuts import redirect
from django.urls import reverse


class CompanySetupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from apps.company.models import Company
        if not Company.objects.exists():
            create_company_url = reverse('company:register_company')
            if request.path != create_company_url and\
                    not request.path.startswith('/static/'):
                return redirect(create_company_url)
        response = self.get_response(request)
        return response
