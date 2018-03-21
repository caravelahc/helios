"""
CAS (Princeton) Authentication

Some code borrowed from
https://sp.princeton.edu/oit/sdp/CAS/Wiki%20Pages/Python.aspx
"""

from __future__ import absolute_import

from cas import CASClient
from django.http import *
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.six.moves import urllib_parse
from django.shortcuts import resolve_url
from django.utils.translation import ugettext_lazy as _

import datetime

_DEFAULTS = {
    'CAS_ADMIN_PREFIX': None,
    'CAS_CREATE_USER': True,
    'CAS_EXTRA_LOGIN_PARAMS': None,
    'CAS_RENEW': False,
    'CAS_IGNORE_REFERER': False,
    'CAS_LOGOUT_COMPLETELY': True,
    'CAS_FORCE_CHANGE_USERNAME_CASE': None,
    'CAS_REDIRECT_URL': '/',
    'CAS_RETRY_LOGIN': False,
    'CAS_SERVER_URL': None,
    'CAS_VERSION': '2',
    'CAS_USERNAME_ATTRIBUTE': 'uid',
    'CAS_PROXY_CALLBACK': None,
    'CAS_LOGIN_MSG': _("Login succeeded. Welcome, %s."),
    'CAS_LOGGED_MSG': _("You are logged in as %s."),
    'CAS_STORE_NEXT': False,
    'CAS_APPLY_ATTRIBUTES_TO_USER': False,
    'CAS_CREATE_USER_WITH_ID': False
}

for key, value in list(_DEFAULTS.items()):
    try:
        getattr(settings, key)
    except AttributeError:
        setattr(settings, key, value)
    # Suppress errors from DJANGO_SETTINGS_MODULE not being set
    except ImportError:
        pass

# display tweaks
LOGIN_MESSAGE = "Log in with my NetID"
STATUS_UPDATES = False


def get_protocol(request):
    """Returns 'http' or 'https' for the request protocol"""
    if request.is_secure():
        return 'https'
    return 'http'


def get_redirect_url(request):
    """Redirects to referring page, or CAS_REDIRECT_URL if no referrer is
    set.
    """
    if request:
        next_ = request.GET.get(REDIRECT_FIELD_NAME)
    else:
        next_ = None

    if not next_:
        redirect_url = resolve_url(settings.CAS_REDIRECT_URL)

        if not request:
            return redirect_url

        if settings.CAS_IGNORE_REFERER:
            next_ = redirect_url
        else:
            next_ = request.META.get('HTTP_REFERER', redirect_url)

        prefix = urllib_parse.urlunparse(
            (get_protocol(request), request.get_host(), '', '', '', ''),
        )
        if next_.startswith(prefix):
            next_ = next_[len(prefix):]

    return next_


def get_service_url(request, redirect_to=None):
    """Generates application django service URL for CAS"""
    protocol = get_protocol(request)
    host = request.get_host()
    service = urllib_parse.urlunparse(
        (protocol, host, request.path, '', '', ''),
    )
    if not settings.CAS_STORE_NEXT:
        if '?' in service:
            service += '&'
        else:
            service += '?'
        service += urllib_parse.urlencode({
            REDIRECT_FIELD_NAME: redirect_to or get_redirect_url(request)
        })
    return service


def get_cas_client(service_url=None, request=None):
    """
    initializes the CASClient according to
    the CAS_* settigs
    """
    # Handle CAS_SERVER_URL without protocol and hostname
    server_url = settings.CAS_SERVER_URL
    if server_url and request and server_url.startswith('/'):
        scheme = request.META.get("X-Forwarded-Proto", request.scheme)
        server_url = scheme + "://" + request.META['HTTP_HOST'] + server_url
    # assert server_url.startswith('http'), "settings.CAS_SERVER_URL invalid"
    return CASClient(
        service_url=service_url,
        version=settings.CAS_VERSION,
        server_url=server_url,
        extra_login_params=settings.CAS_EXTRA_LOGIN_PARAMS,
        renew=settings.CAS_RENEW,
        username_attribute=settings.CAS_USERNAME_ATTRIBUTE,
        proxy_callback=settings.CAS_PROXY_CALLBACK
    )


def get_auth_url(request, redirect_url):
    client = get_cas_client(redirect_url, request)
    return client.get_login_url()


def do_logout(user):
    """
    Perform logout of CAS by redirecting to the CAS logout URL
    """
    # protocol = get_protocol(request)
    # host = request.get_host()
    protocol = 'https'
    host = 'e-democracia.ufsc.br'
    redirect_url = urllib_parse.urlunparse(
        (protocol, host, '', '', '', ''),
    )

    client = get_cas_client(service_url=get_service_url())
    return HttpResponseRedirect(client.get_logout_url(redirect_url))

def get_user_info_after_auth(request):
    ticket = request.GET.get('ticket', None)

    # if no ticket, this is a logout
    if not ticket:
        return None

    service = get_service_url(request)
    client = get_cas_client(service_url=service, request=request)
    username, attributes, pgtiou = client.verify_ticket(ticket)
    if attributes and request:
        request.session['attributes'] = attributes

    return {
        'user_id': attributes['uid'],
        'name': attributes['personName'],
        'info': {
            'name': attributes['personName'],
            'category': attributes['tipoAcessoLogin'],
        },
        'token': None,
        'type': 'cas',
    }


def update_status(token, message):
    """
    simple update
    """
    pass


#
# eligibility
#

def check_constraint(constraint, user):
    if not user.info.has_key('category'):
        return False
    return constraint['year'] == user.info['category']


def generate_constraint(category_id, user):
    """
    generate the proper basic data structure to express a constraint
    based on the category string
    """
    return {'year': category_id}


def list_categories(user):
    current_year = datetime.datetime.now().year
    return [{'id': str(y), 'name': 'Class of %s' % y} for y
            in range(current_year, current_year + 5)]


def eligibility_category_id(constraint):
    return constraint['year']


def pretty_eligibility(constraint):
    return "Members of the Class of %s" % constraint['year']


#
# Election Creation
#

def can_create_election(user_id, user_info):
    return True
