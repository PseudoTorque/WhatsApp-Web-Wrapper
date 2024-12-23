class NotLoggedInException(Exception):
    """
    Exception raised for errors related to not being logged in.
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"NotLoggedInException: {self.message}"

class ClientMessageException(Exception):
    """
    Exception raised for errors related to sending a message to a client.
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"ClientMessageException: {self.message}"
