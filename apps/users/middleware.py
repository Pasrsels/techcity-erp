from django.shortcuts import redirect
from django.urls import reverse

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            # List of paths that don't require authentication
            exempt_urls = [
                reverse('users:login'),
                reverse('users:logout'),
            ]
            
            if request.path not in exempt_urls:
                # Store the current path in session
                request.session['next_url'] = request.path
                return redirect('users:login')
        
        return self.get_response(request)