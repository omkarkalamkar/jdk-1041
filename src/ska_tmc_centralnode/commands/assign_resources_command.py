"""
AssignResources class for CentralNode.
"""
import json

from ska_ser_skuid.client import SkuidClient
from ska_tango_base.commands import ResultCode
from ska_tmc_common.adapters import AdapterFactory

from ska_tmc_centralnode.commands.abstract_command import (
    AbstractAssignReleaseResources,
)


class AssignResources(AbstractAssignReleaseResources):
    """
    A class for CentralNode's AssignResources() command.

    Assigns resources to given subarray. It accepts the subarray id, receptor id list and SDP block in JSON
    string format. Upon successful execution, the 'receptor_ids' attribute of the given subarray is populated
    with the given receptors.Also checking for duplicate allocation of resources is done. If already allocated
    it will throw error message regarding the prior existence of resource.
    """

    def __init__(
        self,
        target,
        pop_state_model,
        adapter_factory=None,
        skuid=SkuidClient(
            "ska-ser-skuid-test-svc.tmcmid.svc.cluster.local:9870"
        ),
        *args,
        logger=None,
        **kwargs,
    ):
        super().__init__(target, args, logger, kwargs)
        self.op_state_model = pop_state_model
        self._adapter_factory = adapter_factory or AdapterFactory()
        self.tm_dish_adapters = []
        self.tm_subarray_adapters = []
        self._skuid = skuid
        self.init_adapters()

    def do_mid(self, argin=None):
        """
        Method to invoke AssignResources command on Subarray.

        :param argin: The string in JSON format. The JSON contains following values:

            subarray_id:
                DevShort. Mandatory.

            dish:
                Mandatory JSON object consisting of

                receptor_ids:
                    DevVarStringArray
                    The individual string should contain dish numbers in string format
                    with preceding zeroes upto 3 digits. E.g. 0001, 0002.

            sdp:
                Mandatory JSON object consisting of

                eb_id:
                    DevString
                    The SBI id.
                max_length:
                    DevDouble
                    Maximum length of the SBI in seconds.
                scan_types:
                    array of the blocks each consisting following parameters
                    scan_type_id:
                       DevString
                       The scan id.
                    coordinate_system:
                       DevString
                    ra:
                       DevString
                    Dec:
                       DevString

                processing_blocks:
                    array of the blocks each consisting following parameters

                    eb_id:
                        DevString
                        The Processing Block id.
                    workflow:
                        kind:
                           DevString
                        name:
                           DevString
                        version:
                           DevString
                    parameters:
                        {}

        Example:
            {"interface":"https://schema.skao.int/ska-tmc-assignresources/2.0",
            "transaction_id":"txn-....-00001","subarray_id":1,"dish":
            {"receptor_ids":["0001","0002"]},"sdp":{"interface":
            "https://schema.skao.int/ska-sdp-assignres/0.3","eb_id":
            "eb-mvp01-20200325-00001","max_length":100.0,"scan_types":
            [{"scan_type_id":"science_A","reference_frame":"ICRS","ra":"02:42:40.771"
            ,"dec":"-00:00:47.84","channels":[{"count":744,"start":0,"stride":2,"freq_min"
            :0.35e9,"freq_max":0.368e9,"link_map":[[0,0],[200,1],[744,2],[944,3]]},
            {"count":744,"start":2000,"stride":1,"freq_min":0.36e9,"freq_max":0.368e9,
            "link_map":[[2000,4],[2200,5]]}]},{"scan_type_id":"calibration_B","reference_frame"
            :"ICRS","ra":"12:29:06.699","dec":"02:03:08.598","channels":[{"count":744,
            "start":0,"stride":2,"freq_min":0.35e9,"freq_max":0.368e9,"link_map":
            [[0,0],[200,1],[744,2],[944,3]]},{"count":744,"start":2000,"stride":1,
            "freq_min":0.36e9,"freq_max":0.368e9,"link_map":[[2000,4],
            [2200,5]]}]}],"processing_blocks":[{"pb_id":"pb-mvp01-20200325-00001"
            ,"workflow":{"kind":"realtime","name":"vis_receive","version":"0.1.0"},
            "parameters":{}},{"pb_id":"pb-mvp01-20200325-00002","workflow":{"kind":"realtime",
            "name":"test_realtime","version":"0.1.0"},"parameters":{}},{"pb_id":"pb-mvp01-20200325-00003",
            "workflow":{"kind":"batch","name":"ical","version":"0.1.0"},"parameters":{},
            "dependencies":[{"pb_id":"pb-mvp01-20200325-00001","kind":["visibilities"]}]},
            {"pb_id":"pb-mvp01-20200325-00004","workflow":{"kind":"batch","name":"dpreb","version":
            "0.1.0"},"parameters":{},"dependencies":[{"pb_id":"pb-mvp01-20200325-00003","kind":["calibration"]}]}]}}


        Note: From Jive, enter above input string without any space.

        return:
            A tuple containing a return code and a string in JSON format on successful assignment
            of given resources. The JSON string contains following values:

            dish:
                Mandatory JSON object consisting of

                receptor_ids_allocated:
                    DevVarStringArray
                    Contains ids of the receptors which are successfully allocated. Empty on unsuccessful
                    allocation.


            Example:
                {
                "dish": {
                "receptor_ids_allocated": ["0001"]
                }
                }

        Note: Enter input without spaces as:{"dish":{"receptor_ids_allocated":["0001"]}}

        return:
            None

        """
        component_manager = self.target

        # TODO: Uncomment this code when CDM library will be aligned as per ADR-35
        # self.logger.info("Validating input string.")
        # input_validator = AssignResourceValidator(
        #     self.tm_mid_subarrays,
        #     device_data._dish_leaf_node_devices,
        #     self.dln_prefix,
        #     self.logger,
        # )
        # json_argument = input_validator.loads(argin)

        try:
            json_argument = json.loads(argin)
        except Exception as e:
            return self.generate_command_result(
                ResultCode.FAILED,
                ("Problem in loading the JSON string: %s", e),
            )

        if "sdp" not in json_argument:
            return self.generate_command_result(
                ResultCode.FAILED,
                "sdp key is not present in the input json argument.",
            )

        if json_argument["sdp"]["eb_id"] == "":
            sdp_keys = list(json_argument["sdp"].keys())
            sdp_values = list(json_argument["sdp"].values())
            id = sdp_keys[sdp_values.index("")]
            try:
                self.update_resource_config_file(json_argument, id)
            except Exception as e:
                return self.generate_command_result(
                    ResultCode.FAILED, ("Errors in input json argument: %s", e)
                )

        # get subarray ID
        if "transaction_id" not in json_argument:
            return self.generate_command_result(
                ResultCode.FAILED,
                "transaction_id key is not present in the input json argument.",
            )

        if "transaction_id" in json_argument:
            del json_argument["transaction_id"]

        if "subarray_id" not in json_argument:
            return self.generate_command_result(
                ResultCode.FAILED,
                "subarray_id key is not present in the input json argument.",
            )

        subarrayID = int(json_argument["subarray_id"])

        my_subarray_adapter = None
        for adapter in self.tm_subarray_adapters:
            if str(subarrayID) in adapter.dev_name:
                my_subarray_adapter = adapter

        if my_subarray_adapter is None:
            return self.generate_command_result(
                ResultCode.FAILED,
                ("SubArray Id %s is not existing!", subarrayID),
            )

        # check allocated dishes
        if "dish" not in json_argument:
            return self.generate_command_result(
                ResultCode.FAILED,
                "dish key is not present in the input json argument.",
            )
        else:
            if "receptor_ids" not in json_argument["dish"]:
                return self.generate_command_result(
                    ResultCode.FAILED,
                    "dish.receptor_ids key is not present in the input json argument.",
                )

        receptor_ids = json_argument["dish"]["receptor_ids"]
        for receptor_id in receptor_ids:
            dish_ID = "dish" + receptor_id
            if component_manager.is_already_assigned(dish_ID):
                return self.generate_command_result(
                    ResultCode.FAILED,
                    ("Dish %s is already allocated", dish_ID),
                )

        try:
            # is it necessary to make a copy? leave it as it was. MDC 29 Sept 2021
            resources_allocated_return = my_subarray_adapter.AssignResources(
                json.dumps(json_argument.copy())
            )
            self.logger.info(
                "Command result from Subarray: %s", resources_allocated_return
            )
            # Leave the monitoring loop to do the updates on the allocated resources!
            return (ResultCode.OK, "")
        except Exception as e:
            return self.generate_command_result(
                ResultCode.FAILED,
                (
                    "Error in calling AssignResources on subarray %s: %s",
                    my_subarray_adapter.dev_name,
                    e,
                ),
            )

    def update_resource_config_file(self, json_argument, id):
        """This method utilizes SKUID service to generate unique sb_id / eb_id and pb_id"""
        # New type of id "eb_id" is used to distinguish between real SB and id used during testing
        unique_id = self._skuid.fetch_skuid("eb")
        json_argument["sdp"][id] = unique_id
        if "processing_blocks" in json_argument["sdp"]:
            for i in range(len(json_argument["sdp"]["processing_blocks"])):
                pb_id = self._skuid.fetch_skuid("pb")
                json_argument["sdp"]["processing_blocks"][i]["pb_id"] = pb_id
                if (
                    "dependencies"
                    in json_argument["sdp"]["processing_blocks"][i]
                ):
                    if i == 0:
                        json_argument["sdp"]["processing_blocks"][i][
                            "dependencies"
                        ][0]["pb_id"] = json_argument["sdp"][
                            "processing_blocks"
                        ][
                            i
                        ][
                            "pb_id"
                        ]
                    else:
                        json_argument["sdp"]["processing_blocks"][i][
                            "dependencies"
                        ][0]["pb_id"] = json_argument["sdp"][
                            "processing_blocks"
                        ][
                            i - 1
                        ][
                            "pb_id"
                        ]
        else:
            raise Exception(
                "processing_blocks key not present in the input json argument"
            )

    def do_low(self, argin=None):
        """
        Method to invoke AssignResources command on Subarray.

        :param argin: The string in JSON format. The JSON contains following values:
            interface:
                DevString. Mandatory.
                Version of schema to allocate assign resources.

            subarray_id:
                DevShort. Mandatory.
                Sub-Array to allocate resources to

            mccs:
                subarray_beam_ids:
                    DevArray. Mandatory
                    logical ID of beam
                station_ids:
                    DevArray. Mandatory
                    list of stations contributing beams to the data set
                channel_blocks:
                    DevArray. Mandatory
                    list of channels used


        Example:
            {"interface":"https://schema.skao.int/ska-low-tmc-assignresources/2.0","transaction_id":"txn-....-00001","subarray_id":1,"mccs":{"subarray_beam_ids":[1],"station_ids":[[1,2]],"channel_blocks":[3]},"sdp":{}}

        Note: Enter input without spaces as:
        {"interface":"https://schema.skao.int/ska-low-tmc-assignresources/2.0",
        "transaction_id":"txn-....-00001","subarray_id":1,"mccs":{"subarray_beam_ids":[1],
        "station_ids":[[1,2]],
        "channel_blocks":[3]},"sdp":{}}
        return:
            None

        raises:
            KeyError if input argument json string contains invalid key

            ValueError if input argument json string contains invalid value

            AssertionError if  Mccs On command is not completed.

        """
        try:
            json_argument = json.loads(argin)
        except Exception as e:
            return self.generate_command_result(
                ResultCode.FAILED,
                ("Problem in loading the JSON string: %s", e),
            )

        if "subarray_id" not in json_argument:
            return self.generate_command_result(
                ResultCode.FAILED,
                "subarray_id key is not present in the input json argument.",
            )

        if "mccs" not in json_argument:
            return self.generate_command_result(
                ResultCode.FAILED,
                "mccs key is not present in the input json argument.",
            )

        if "subarray_beam_ids" not in json_argument["mccs"]:
            return self.generate_command_result(
                ResultCode.FAILED,
                "mccs.subarray_beam_ids key is not present in the input json argument.",
            )

        if "station_ids" not in json_argument["mccs"]:
            return self.generate_command_result(
                ResultCode.FAILED,
                "mccs.station_ids key is not present in the input json argument.",
            )

        if "channel_blocks" not in json_argument["mccs"]:
            return self.generate_command_result(
                ResultCode.FAILED,
                "mccs.channel_blocks key is not present in the input json argument.",
            )

        if "transaction_id" not in json_argument:
            return self.generate_command_result(
                ResultCode.FAILED,
                "transaction_id key is not present in the input json argument.",
            )

        subarrayID = int(json_argument["subarray_id"])

        my_subarray_adapter = None
        for adapter in self.tm_subarray_adapters:
            if str(subarrayID) in adapter.dev_name:
                my_subarray_adapter = adapter

        if my_subarray_adapter is None:
            return self.generate_command_result(
                ResultCode.FAILED,
                ("SubArray Id %s is not existing!", subarrayID),
            )

        try:
            subarray_cmd_data = self.create_subarray_cmd_data(json_argument)
        except Exception as e:
            return self.generate_command_result(
                ResultCode.FAILED, ("Errors in input json argument: %s", e)
            )

        try:
            my_subarray_adapter.AssignResources(subarray_cmd_data)
        except Exception as e:
            return self.generate_command_result(
                ResultCode.FAILED,
                (
                    "Error in calling AssignResources on subarray %s: %s",
                    my_subarray_adapter.dev_name,
                    e,
                ),
            )

        try:
            input_mccs_master = self.create_mccs_cmd_data(json_argument)
        except Exception as e:
            return self.generate_command_result(
                ResultCode.FAILED, ("Errors in input json argument: %s", e)
            )

        try:
            self.tm_leaf_mccs_master_adapter.AssignResources(input_mccs_master)
        except Exception as e:
            return self.generate_command_result(
                ResultCode.FAILED,
                f"Error in calling AssignResource command on TM MCCS Master Leaf {self.tm_leaf_mccs_master_adapter.dev_name}: {e}",
            )

        return (ResultCode.OK, "")

    def create_mccs_cmd_data(self, json_argument):
        """
        Remove 'sdp' and 'mccs' key from input JSON argument and forward the updated JSON to mccs master leaf node.

        :param json_argument: The string in JSON format.

        :return: The string in JSON format.
        """
        mccs_value = json_argument["mccs"]
        json_argument[
            "interface"
        ] = "https://schema.skao.int/ska-low-mccs-assignresources/1.0"
        if "transaction_id" in json_argument:
            del json_argument["transaction_id"]
        if "sdp" in json_argument:
            del json_argument["sdp"]
        if "mccs" in json_argument:
            del json_argument["mccs"]
        json_argument.update(mccs_value)
        input_to_mccs = json.dumps(json_argument)
        return input_to_mccs

    def create_subarray_cmd_data(self, json_argument):
        """
        Remove 'subarray id', 'sdp' from json argument and forward the updated JSON to Subarray node.

        :param json_argument: The string in JSON format.

        :return: The string in JSON format.
        """
        # Remove subarray_id key from input json argument and send the json to subarray node
        if "subarray_id" in json_argument:
            del json_argument["subarray_id"]
        if "sdp" in json_argument:
            del json_argument["sdp"]
        input_to_subarray = json.dumps(json_argument)
        return input_to_subarray
