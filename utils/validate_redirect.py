from django.utils.http import url_has_allowed_host_and_scheme

def is_safe_url(url, allowed_hosts):
    """
    Verify that the URL is safe to redirect to by checking the host
    against the allowed hosts.
    """
    return url_has_allowed_host_and_scheme(url, allowed_hosts=allowed_hosts)
