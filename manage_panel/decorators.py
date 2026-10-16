from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import Http404


def staff_required(view):
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise Http404
        return view(request, *args, **kwargs)
    return wrapper