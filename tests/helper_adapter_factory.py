import mock
from ska_tmc_centralnode_mid.manager.adapters import AdapterFactory, AdapterType, Dish, CspMaster, BaseAdapter

class HelperAdapterFactory(AdapterFactory):
    def __init__(self) -> None:
        self.adapters = []

    def get_or_create_adapter(self, dev_name, adapter_type = AdapterType.BASE):
        for adapter in self.adapters:
            if adapter.dev_name == dev_name:
                return adapter

        new_adapter = None
        if adapter_type ==  AdapterType.DISH:
            new_adapter = Dish(dev_name, mock.Mock())
        elif adapter_type == AdapterType.CSP:
            new_adapter = CspMaster(dev_name, mock.Mock())
        else:
            new_adapter = BaseAdapter(dev_name, mock.Mock())

        self.adapters.append(new_adapter)
        return new_adapter
