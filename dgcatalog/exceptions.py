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

    def __str__(self):
        if not self.message:
            return "StacException"
        message = self.message
        if self.request_id:
            message += ' (Request ID: {})'.format(self.request_id)
        return message
