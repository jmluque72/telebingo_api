#!/usr/bin/env python
# -*- coding: UTF-8 -*-

class LastVisitedMiddleware(object):
    """This middleware sets the last five visited urls as session field.
    It ignores POSTs"""

    def process_request(self, request):
        """Intercept the request and add the current path to it"""

        if request.method == 'POST':
            return

        request_path = request.get_full_path()
        request.session['currently_visiting'] = request_path
        try:
            visited = request.session.get('recently_visited', [])
            visited.insert(0, request.session['currently_visiting'])
            request.session['recently_visited'] = visited[:5]
        except KeyError:
            # silence the exception - this is the users first request
            pass
