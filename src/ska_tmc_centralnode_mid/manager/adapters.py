


class BaseAdapter:

    def __init__(self, dev_name, proxy) -> None:
        self._proxy = proxy
        self._dev_name = dev_name

    @property
    def proxy(self):
        return self._proxy

    @property
    def dev_name(self):
        return self._dev_name

    def On(self):
        self.proxy.On()

    def Off(self):
        self.proxy.On()
    
    def __eq__(self, other):
        if (isinstance(other, BaseAdapter)):
            return self.dev_name == other.dev_name
        else:
            return False


class CspMaster(BaseAdapter):

    def __init__(self, proxy, validator) -> None:
        self._proxy = proxy
        self._validator = validator

    def AssignResources(self, value):
        pass