#
# exceptions.py
#


class StacException(Exception):
    def __init__(self, message, response=None, request_id=None):
        """
        An exception from the STAC catalog web service

        :param message: User-friendly error message
        :param response: Optional requests.Response object (See http://docs.python-requests.org/en/master/api/#requests.Response)
        :param request_id: Optional request ID
        """
        self.message = message
        self.response = response
        self.request_id = request_id
