
import enum
from ska_tmc_centralnode_mid.dev_factory import DevFactory

class AdapterType(enum.IntEnum):
    BASE = 0
    CSP = 1
    DISH = 2

class AdapterFactory():

    def __init__(self) -> None:
        self._adapters = []
        self._dev_factory = DevFactory()

    def get_or_create_adapter(self, dev_name, adapter_type = AdapterType.BASE):
        """
        Get or create a generic adapter 

        :param dev_name: device name
        :type str
        """
        for adapter in self._adapters:
            if adapter.dev_name == dev_name:
                return adapter

        new_adapter = None
        if adapter_type ==  AdapterType.DISH:
            new_adapter = Dish(dev_name, self._dev_factory.get_device(dev_name))
        elif adapter_type == AdapterType.CSP:
            new_adapter = CspMaster(dev_name, self._dev_factory.get_device(dev_name))
        else:
            new_adapter = BaseAdapter(dev_name, self._dev_factory.get_device(dev_name))

        self._adapters.append(new_adapter)
        return new_adapter

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
        self.proxy.TelescopeOn()

    def Off(self):
        self.proxy.TelescopeOff()

    def StandBy(self):
        self.proxy.TelescopeStandBy()
    
    def __eq__(self, other):
        if (isinstance(other, BaseAdapter)):
            return self.dev_name == other.dev_name
        else:
            return False

class CspMaster(BaseAdapter):

    def __init__(self, dev_name, proxy) -> None:
        super().__init__(dev_name, proxy)

    def AssignResources(self, value):
        self._proxy.AssignResources(value)


class Dish(BaseAdapter):

    def __init__(self, dev_name, proxy) -> None:
        super().__init__(dev_name, proxy)

    def SetStandbyFPMode(self):
        self._proxy.SetStandbyFPMode()

    def SetOperateMode(self):
        self._proxy.SetOperateMode()

    def SetStandbyLPMode(self):
        self._proxy.SetStandbyLPMode()

    def SetStowMode(self):
        self._proxy.SetStowMode()
