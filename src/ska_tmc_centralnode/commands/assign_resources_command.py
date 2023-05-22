"""
AssignResources class for CentralNode.
"""
import json
import threading
from typing import Callable, Optional, Tuple

from ska_ser_skuid.client import SkuidClient
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

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
        component_manager,
        adapter_factory=None,
        skuid=SkuidClient(
            "ska-ser-skuid-test-svc.ska-tmc-centralnode.svc.cluster.local:9870"
        ),
        *args,
        logger=None,
        **kwargs,
    ):
        super().__init__(
            component_manager, adapter_factory, logger=logger, *args, **kwargs
        )
        self.dish_adapters = []
        self.subarray_adapters = []
        self.my_subarray_adapter = None
        self._skuid = skuid
        self.task_callback: Callable

    def assign_resources(
        self,
        argin,
        logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ):

        """This is a long running method for TelescopeOn command, it executes do hook,
        invokes TelescopeOn command on lowe level devices.

        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """
        # Indicate that the task has started
        self.task_callback = task_callback
        task_callback(status=TaskStatus.IN_PROGRESS)
        self.component_manager.command_in_progress = "AssignResources"
        self.component_manager.command_result = ResultCode.STARTED

        ret_code, message = self.do(argin=json.dumps(argin))
        self.logger.info(message)
        if ret_code == ResultCode.FAILED:
            self.update_task_status(ret_code, message)
        else:
            self.start_tracker_thread(
                self.component_manager.get_command_result,
                ResultCode.OK,
                command_id=self.component_manager.assign_id,
                lrcr_callback=self.component_manager.long_running_result_callback,
            )

    def update_task_status(self, result: ResultCode, message: str = ""):
        """Updates the task status for command"""
        if result == ResultCode.FAILED:
            self.task_callback(
                result=result, status=TaskStatus.COMPLETED, exception=message
            )
        else:
            self.task_callback(result=result, status=TaskStatus.COMPLETED)

    def do_mid(self, argin) -> Tuple[ResultCode, str]:
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
                        with preceding zeroes upto 3 digits. E.g. SKA001, SKA002.

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
        {"interface":"https://schema.skao.int/ska-tmc-assignresources/2.1",
        "transaction_id":"txn-....-00001","subarray_id":1,"dish":{"receptor_ids":
        ["SKA001"]},"sdp":{"interface":"https://schema.skao.int/ska-sdp-assignres/0.4",
        "execution_block":{"eb_id":"eb-mvp01-20200325-00001","max_length": 100,"context":
        {},"beams":[{"beam_id":"vis0","function":"visibilities"}],"scan_types":[{
        "scan_type_id":".default","beams":{"vis0":{"channels_id":"vis_channels",
        "polarisations_id":"all"}}},{"scan_type_id":"target:a","derive_from":
        ".default","beams":{"vis0":{"field_id": "field_a"}}}],"channels":[{
        "channels_id":"vis_channels","spectral_windows":[{"spectral_window_id":
        "fsp_1_channels","count": 744,"start": 0,"stride": 2,"freq_min": 350000000,
        "freq_max": 368000000,"link_map":[[0,0],[200,1],[744,2],[944,3]]},
        {"spectral_window_id":"fsp_2_channels","count":744,"start":2000,"stride":1,
        "freq_min": 360000000,"freq_max": 368000000,"link_map":[[2000,4],[2200,5]]},
        {"spectral_window_id":"zoom_window_1","count": 744,"start":4000,"stride": 1,
        "freq_min":360000000,"freq_max":361000000,"link_map":[[4000,6],[4200,7]]}]}],
        "polarisations":[{"polarisations_id":"all","corr_type":["XX","XY","YY","YX"]}],
        "fields":[{"field_id":"field_a","phase_dir":{"ra":[123,0.1],"dec":[123,0.1],
        "reference_time": "...","reference_frame":"ICRF3"},"pointing_fqdn":"low-tmc/telstate/0/pointing"}]},
        "processing_blocks": [{"pb_id":"pb-mvp01-20200325-00003","sbi_ids":["sbi-mvp01-20200325-00001", "sbi-mvp01-20200325-00002" ],
        "script":{},"parameters":{},"dependencies":{}}],"resources":{"csp_links":[1,2,3,4],"receptors":
        ["FS4","FS8"],"receive_nodes":10}}}


            Note: From Jive, enter above input string without any space.

            return:
                A tuple containing a return code and a string msg.
                For Example:
                    (ResultCode.OK, "")

        """
        try:
            self.logger.debug(f"Loading json string:{argin}")
            json_argument = json.loads(argin)
        except Exception as e:
            return (
                ResultCode.FAILED,
                f"Problem in loading the JSON string: {e}",
            )

        if "transaction_id" in json_argument:
            del json_argument["transaction_id"]

        ret_code, message = self.init_adapters()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        subarrayID = int(json_argument["subarray_id"])

        ret_code, message = self.get_subarray_adapter(subarrayID)
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        receptor_ids = json_argument["dish"]["receptor_ids"]
        self.logger.debug(f"receptor_ids are:{receptor_ids}")
        for receptor_id in receptor_ids:
            dish_id = "dish0" + receptor_id[3:]
            self.logger.debug(f"dish_id is:{dish_id}")
            if self.component_manager.is_already_assigned(dish_id):
                return (
                    ResultCode.FAILED,
                    f"Dish {dish_id} is already allocated",
                )
            else:
                self.logger.info("Resources are already assigned")
        self.component_manager.log_state(
            "Device states before executing AssignResources command"
        )

        self.logger.debug(
            f"Invoking AssignResources command on:{self.my_subarray_adapter}"
        )

        # is it necessary to make a copy? leave it as it was. MDC 29 Sept 2021
        ret_code, message = self.send_command(
            [self.my_subarray_adapter],
            "Error in calling AssignResources on subarray",
            "AssignResources",
            json.dumps(json_argument),
        )

        if ret_code == ResultCode.FAILED:
            return ret_code, message
        self.logger.debug(
            f"Resources assigned successfully to:{self.my_subarray_adapter}"
        )

        return (ResultCode.OK, "")

    def update_resource_config_file(self, json_argument, id):
        """This method utilizes SKUID service to generate unique sb_id / eb_id and pb_id"""
        # New type of id "eb_id" is used to distinguish between real SB and id used during testing
        unique_id = self._skuid.fetch_skuid("eb")
        json_argument["sdp"]["execution_block"][id] = unique_id
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
        {"interface":"https://schema.skao.int/ska-low-tmc-assignresources/3.0","transaction_id":"txn-....-00001","subarray_id":1,
        "mccs":{"subarray_beam_ids":[1],"station_ids":[[1,2]],"channel_blocks":[3]},
        "sdp":{"interface":"https://schema.skao.int/ska-sdp-assignres/0.4","execution_block":{"eb_id":"eb-mvp01-20200325-00001",
        "max_length":100,"context":{},"beams":[{"beam_id":"vis0","function":"visibilities"},
        {"beam_id":"pss1","search_beam_id":1,"function":"pulsar search"},{"beam_id":"pss2","search_beam_id":2,"function":"pulsar search"},
        {"beam_id":"pst1","timing_beam_id":1,"function":"pulsar timing"},{"beam_id":"pst2","timing_beam_id":2,"function":"pulsar timing"},
        {"beam_id":"vlbi1","vlbi_beam_id":1,"function":"vlbi"}],
        "scan_types":[{"scan_type_id":".default","beams":{"vis0":{"channels_id":"vis_channels","polarisations_id":"all"},
        "pss1":{"field_id":"pss_field_0","channels_id":"pulsar_channels","polarisations_id":"all"},
        "pss2":{"field_id":"pss_field_1","channels_id":"pulsar_channels","polarisations_id":"all"},
        "pst1":{"field_id":"pst_field_0","channels_id":"pulsar_channels","polarisations_id":"all"},
        "pst2":{"field_id":"pst_field_1","channels_id":"pulsar_channels","polarisations_id":"all"},
        "vlbi":{"field_id":"vlbi_field","channels_id":"vlbi_channels","polarisations_id":"all"}}},
        {"scan_type_id":"target:a","derive_from":".default","beams":{"vis0":{"field_id":"field_a"}}}],
        "channels":[{"channels_id":"vis_channels",
        "spectral_windows":[{"spectral_window_id":
        "fsp_1_channels","count":744,"start":0,"stride":2,"freq_min":350000000,"freq_max":368000000,
        "link_map":[[0,0],[200,1],[744,2],[944,3]]},{"spectral_window_id":"fsp_2_channels",
        "count":744,"start":2000,"stride":1,"freq_min":360000000,"freq_max":368000000,"link_map":[[2000,4],[2200,5]]},
        {"spectral_window_id":"zoom_window_1","count":744,"start":4000,"stride":1,"freq_min":360000000,"freq_max":361000000,"link_map":[[4000,6],[4200,7]]}]},
        {"channels_id":"pulsar_channels","spectral_windows":[{"spectral_window_id":"pulsar_fsp_channels","count":744,"start":0,"freq_min":350000000,"freq_max":368000000}]}],
        "polarisations":[{"polarisations_id":"all","corr_type":["XX","XY","YY","YX"]}],"fields":[{"field_id":"field_a",
        "phase_dir":{"ra":[123,0.1],"dec":[123,0.1],"reference_time":"...","reference_frame":"ICRF3"},"pointing_fqdn":"low-tmc/telstate/0/pointing"}]},
        "processing_blocks":[{"pb_id":"pb-mvp01-20200325-00001","sbi_ids":["sbi-mvp01-20200325-00001"],"script":{},"parameters":{},
        "dependencies":{}},{"pb_id":"pb-mvp01-20200325-00002","sbi_ids":["sbi-mvp01-20200325-00002"],"script":{},"parameters":{},
        "dependencies":{}},{"pb_id":"pb-mvp01-20200325-00003","sbi_ids":["sbi-mvp01-20200325-00001","sbi-mvp01-20200325-00002"],"script":{},
        "parameters":{},"dependencies":{}}],"resources":{"csp_links":[1,2,3,4],"receptors":["FS4","FS8"],"receive_nodes":10}},
        "csp":{"interface":"https://schema.skao.int/ska-low-csp-assignresources/2.0","common":{"subarray_id":1},
        "lowcbf":{"resources":[{"device":"fsp_01","shared":true,"fw_image":"pst","fw_mode":"unused"},
        {"device":"p4_01","shared":true,"fw_image":"p4.bin","fw_mode":"p4"}]}}}


        Note: From Jive, enter above input string without any space.

        return:
            None

        raises:
            KeyError if input argument json string contains invalid key

            ValueError if input argument json string contains invalid value

            AssertionError if  Mccs On command is not completed.

        """
        try:
            json_argument = json.loads(argin)
            self.logger.debug(f"Loading json string:{argin}")
        except Exception as e:
            return (
                ResultCode.FAILED,
                ("Problem in loading the JSON string: %s", e),
            )

        ret_code, message = self.init_adapters()
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        subarrayID = int(json_argument["subarray_id"])

        ret_code, message = self.get_subarray_adapter(subarrayID)
        if ret_code == ResultCode.FAILED:
            return ret_code, message

        if self.my_subarray_adapter is None:
            return (
                ResultCode.FAILED,
                ("SubArray Id %s is not existing!", subarrayID),
            )

        # TODO Uncomment below code during integrating of MCCS
        # try:
        #     input_mccs_master = self.create_mccs_cmd_data(json_argument)
        # except Exception as e:
        #     return (
        #         ResultCode.FAILED, ("Errors in input json argument: %s", e)
        #     )

        self.component_manager.log_state(
            "Device states before executing AssignResources command"
        )
        for ret_code, message in [
            self.send_command(
                [self.my_subarray_adapter],
                f"Error in calling AssignResources on subarray: {self.my_subarray_adapter.dev_name}",
                "AssignResources",
                json.dumps(json_argument),
            ),
            # self.send_command(
            #     [self.tm_leaf_mccs_master_adapter],
            #     "Error in calling AssignResource command on TM MCCS Master Leaf",
            #     "AssignResources",
            #     input_mccs_master,
            # ),
        ]:
            if ret_code == ResultCode.FAILED:
                return ResultCode.FAILED, message
        return (ResultCode.OK, "")

    def _validate_low_json(self, json_argument, req_keys):
        """To validate the low json for assign resources command before entering the queue
        Args:
            json_argument (dict): Json Argument
            req_keys (list): Required key list to check in json argument
        """
        json_keys = json_argument.keys()
        for key in req_keys:
            if key not in json_keys:
                return (
                    False,
                    f"{key} key is not present in the input json argument.",
                )
        return (
            True,
            "The json argument has all the required keys. Validation successful.",
        )

    # TODO Uncomment below code during integration of MCCS
    # Validate MCCS keys
    # mccs_json = json_argument.get("mccs", {})
    # mccs_error_msg = (
    #     "mccs.{key} key is not present in the input json argument."
    # )
    # is_valid, return_error = self._validate_keys_in_json(
    #     mccs_json, MCCS_REQUIRED_KEYS, mccs_error_msg
    # )
    # if not is_valid:
    #     return is_valid, return_error

    def _validate_and_update_resource_config(self, json_argument):
        """Validate if eb_id present in sdp schema.
        Args:
            json_argument (dict): low json
        """
        try:
            if (
                json_argument["sdp"].get("execution_block")
                and not json_argument["sdp"]["execution_block"]["eb_id"]
            ):
                sdp_keys = list(json_argument["sdp"]["execution_block"].keys())
                sdp_values = list(
                    json_argument["sdp"]["execution_block"].values()
                )
                sdp_id = sdp_keys[sdp_values.index("")]
                self.update_resource_config_file(json_argument, sdp_id)
            return True, ""
        except Exception as e:
            return False, ("Error while updating SDP schema: %s", e)

    # TODO Uncomment below code during integrating of MCCS
    # def create_mccs_cmd_data(self, json_argument):
    #     """
    #     Remove 'sdp' and 'mccs' key from input JSON argument and forward the updated JSON to mccs master leaf node.

    #     :param json_argument: The string in JSON format.

    #     :return: The string in JSON format.
    #     """
    #     mccs_value = json_argument["mccs"]
    #     json_argument[
    #         "interface"
    #     ] = "https://schema.skao.int/ska-low-mccs-assignresources/1.0"
    #     if "transaction_id" in json_argument:
    #         del json_argument["transaction_id"]
    #     if "sdp" in json_argument:
    #         del json_argument["sdp"]
    #     if "mccs" in json_argument:
    #         del json_argument["mccs"]
    #     json_argument.update(mccs_value)
    #     input_to_mccs = json.dumps(json_argument)
    #     return input_to_mccs

    def get_subarray_adapter(self, subarray_id):
        for adapter in self.subarray_adapters:
            if str(subarray_id) in adapter.dev_name:
                self.my_subarray_adapter = adapter

        if self.my_subarray_adapter is None:
            return (
                ResultCode.FAILED,
                f"SubArray Id {subarray_id} is not existing!",
            )

        return ResultCode.OK, ""
