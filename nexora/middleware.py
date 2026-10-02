"""
middleware.py

Custom session handling for Nexora.

DualSessionMiddleware
----------------------
By default, Django's admin and the main app share one session
cookie -- logging into /admin/ as a superuser also logs that
same browser into the main app as a regular user, and vice
versa, since there's only one login system underneath.

This middleware gives /admin/ its own separate session cookie
("admin_sessionid") so the two logins are fully independent:
logging into Django admin no longer logs you into Nexora as a
"student" user, and logging into Nexora normally has no effect
on your admin session.

It mirrors Django's built-in SessionMiddleware exactly, just
choosing which cookie name to read/write based on the request
path, computed fresh per-request (not stored on self) so it's
safe under concurrent requests.
"""

import time

from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date


class DualSessionMiddleware(SessionMiddleware):

    ADMIN_COOKIE_NAME = "admin_sessionid"

    def _cookie_name_for(self, request):
        if request.path.startswith("/admin/"):
            return self.ADMIN_COOKIE_NAME
        return settings.SESSION_COOKIE_NAME

    def process_request(self, request):
        cookie_name = self._cookie_name_for(request)
        session_key = request.COOKIES.get(cookie_name)
        request.session = self.SessionStore(session_key)

    def process_response(self, request, response):

        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response

        patch_vary_headers(response, ("Cookie",))

        cookie_name = self._cookie_name_for(request)

        if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:

            if request.session.get_expire_at_browser_close():
                max_age = None
                expires = None
            else:
                max_age = request.session.get_expiry_age()
                expires_time = time.time() + max_age
                expires = http_date(expires_time)

            if response.status_code != 500:

                request.session.save()

                response.set_cookie(
                    cookie_name,
                    request.session.session_key,
                    max_age=max_age,
                    expires=expires,
                    domain=settings.SESSION_COOKIE_DOMAIN,
                    path=settings.SESSION_COOKIE_PATH,
                    secure=settings.SESSION_COOKIE_SECURE or None,
                    httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                    samesite=settings.SESSION_COOKIE_SAMESITE,
                )

        else:

            if empty and request.COOKIES.get(cookie_name):

                response.delete_cookie(
                    cookie_name,
                    path=settings.SESSION_COOKIE_PATH,
                    domain=settings.SESSION_COOKIE_DOMAIN,
                    samesite=settings.SESSION_COOKIE_SAMESITE,
                )

        return response
