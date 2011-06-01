from django.conf import settings

def hookbox(request):
    return {'HOOKBOX_URL': settings.HOOKBOX_URL}
