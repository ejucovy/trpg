from django.http import HttpResponse
import os
import pkg_resources

def static_view(request, path):
    fp = pkg_resources.resource_stream("main", "static/%s" % path)
    resp = HttpResponse(fp.read())
    fp.close()
    return resp
