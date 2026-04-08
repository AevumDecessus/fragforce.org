from django.conf import settings
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_safe
from django.views.decorators.vary import vary_on_cookie


@require_safe
@cache_page(settings.VIEW_SITE_STATIC_CACHE)
@vary_on_cookie
def home(request):
    """ Home page """
    return render(request, 'ff/root/home.html', {})


# @cache_page(settings.VIEW_SITE_STATIC_CACHE)
@require_safe
def donate(request):
    """ How to donate page """
    from ..utils import random_contact
    return render(request, 'ff/root/donate.html', {
        'rnd_pct': random_contact(),
    })


@require_safe
@cache_page(settings.VIEW_SITE_STATIC_CACHE)
@vary_on_cookie
def join(request):
    """ How to join ff page """
    return render(request, 'ff/root/join.html', {})


@require_safe
@cache_page(settings.VIEW_SITE_STATIC_CACHE)
@vary_on_cookie
def contact(request):
    """ Contact page """
    return render(request, 'ff/root/contact.html', {})


@require_safe
@cache_page(settings.VIEW_SITE_STATIC_CACHE)
@vary_on_cookie
def stream(request):
    """ Stream page """
    return render(request, 'ff/root/stream.html', {
        "stream_url": settings.STREAM_URL,
    })


@require_safe
def login_error(request):
    """ Shown when a user fails OAuth login - typically not a Fragforce guild member """
    return render(request, 'ff/root/login_error.html', {})
