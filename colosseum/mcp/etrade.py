from .base import BrokerMCPServer, NewsMCPServer

class ETradeMCP(BrokerMCPServer, NewsMCPServer):
    def __init__(self, config):
        self.config = config

    def get_resource(self, resource_type, **kwargs):
        # Implement ETrade API calls here for both broker and news/bookmap resources
        pass
