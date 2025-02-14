def get_api_settings(name="FDMS"):
    try:
        settings = APISettings.objects.get(name=name)
        return {
            "api_key": settings.api_key,
            "cert": settings.cert,
            "private_key": settings.private_key,
        }
    except APISettings.DoesNotExist:
        raise ValueError(f"API settings for {name} not found.")
