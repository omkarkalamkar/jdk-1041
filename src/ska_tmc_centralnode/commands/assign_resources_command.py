"""
AssignResources class for CentralNode.
"""
import json
import threading
from logging import Logger
from typing import Callable, List, Optional, Tuple

from ska_ser_skuid.client import SkuidClient
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_base.executor import TaskStatus
from ska_tmc_common.adapters import AdapterFactory

from ska_tmc_centralnode.commands.central_node_command import (
    AssignReleaseResources,
)


class AssignResources(AssignReleaseResources):
    """
    A class for CentralNode's AssignResources() command.

    Assigns resources to given subarray. It accepts the subarray id,
    receptor id list and SDP block in JSON
    string format. Upon successful execution, the 'receptor_ids'
    attribute of the given subarray is populated
    with the given receptors.Also checking for duplicate allocation
    of resources is done. If already allocated
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
        self.tm_subarray_adapter: Optional[AdapterFactory] = None
        self._skuid: SkuidClient = skuid

    def assign_resources(
        self,
        argin: str,
        logger: Logger,
        task_callback: Callable = None,
        task_abort_event: Optional[threading.Event] = None,
    ):
        """This is a long running method for AssignResources command,
          it executes do hook,
        invokes AssignResources command on lower level devices.

        :param logger: logger
        :type logger: logging.Logger
        :param task_callback: Update task state, defaults to None
        :type task_callback: Callable, optional
        :param task_abort_event: Check for abort, defaults to None
        :type task_abort_event: Event, optional
        """
        # Indicate that the task has started
        self.task_callback = task_callback
        self.set_command_id(__class__.__name__)
        task_callback(status=TaskStatus.IN_PROGRESS)
        self.component_manager.command_in_progress = "AssignResources"
        self.component_manager.command_result = ResultCode.STARTED
        self.component_manager.start_timer(
            self.timeout_id,
            self.component_manager.command_timeout,
            self.timeout_callback,
        )

        result_code, message = self.do(argin=json.dumps(argin))
        self.logger.info(f"command assign_resources returncode: {result_code}")
        self.logger.info(message)
        if result_code == ResultCode.FAILED:
            self.update_task_status(result_code, message)
            self.component_manager.stop_timer()
        else:
            self.start_tracker_thread(
                "get_subarray_obsstate",
                [ObsState.RESOURCING, ObsState.IDLE],
                task_abort_event,
                timeout_id=self.timeout_id,
                timeout_callback=self.timeout_callback,
                command_id=self.component_manager.command_id,
                lrcr_callback=(
                    self.component_manager.long_running_result_callback
                ),
            )

    def update_task_status(
        self, result: ResultCode, message: str = ""
    ) -> None:
        """Updates the task status for command"""
        if result == ResultCode.FAILED:
            self.task_callback(
                result=result, status=TaskStatus.COMPLETED, exception=message
            )
            self.component_manager.subarray_devname = ""
        else:
            self.task_callback(result=result, status=TaskStatus.COMPLETED)
        self.component_manager.command_in_progress = ""
        if self.component_manager.command_mapping.get(
            self.component_manager.command_id
        ):
            self.component_manager.command_mapping.pop(
                self.component_manager.command_id
            )

    def do_mid(self, argin: str) -> Tuple[ResultCode, str]:
        """
            Method to invoke AssignResources command on Subarray.

            :param argin: DevString

        Example:

        .. code-block::

        {"interface": "https://schema.skao.int/ska-tmc-assignresources/2.1",
        "transaction_id":
        "txn-....-00001","subarray_id": 1,"dish": {"receptor_ids": ["SKA001"]},
        "sdp": {
        "interface": "https://schema.skao.int/ska-sdp-assignres/0.4",
        "execution_block": {"eb_id": "eb-mvp01-20210623-00000","max_length":
          100.0,
        "context": {},"beams": [{"beam_id": "vis0","function": "visibilities"},
          {
        "beam_id": "pss1","search_beam_id": 1,"function": "pulsar search"},
          {"beam_id": "pss2",
        "search_beam_id": 2,"function": "pulsar search"}, {"beam_id": "pst1",
        "timing_beam_id": 1,"function": "pulsar timing"}, {"beam_id": "pst2",
        "timing_beam_id": 2,
        "function": "pulsar timing"}, {"beam_id": "vlbi1","vlbi_beam_id": 1,
        "function": "vlbi"}],
        "scan_types": [{"scan_type_id": ".default","beams": {"vis0":
        {"channels_id": "vis_channels",
        "polarisations_id": "all"},"pss1": {"field_id": "pss_field_0",
        "channels_id": "pulsar_channels",
        "polarisations_id": "all"},"pss2": {"field_id": "pss_field_1",
        "channels_id": "pulsar_channels",
        "polarisations_id": "all"},"pst1": {"field_id": "pst_field_0",
        "channels_id": "pulsar_channels",
        "polarisations_id": "all"},"pst2": {"field_id": "pst_field_1",
        "channels_id": "pulsar_channels",
        "polarisations_id": "all"},"vlbi": {"field_id": "vlbi_field",
        "channels_id": "vlbi_channels",
        "polarisations_id": "all"}}}, {"scan_type_id": "target:a",
        "derive_from": ".default",
        "beams": {"vis0": {"field_id": "field_a"}}}],"channels":
          [{"channels_id": "vis_channels",
        "spectral_windows": [{"spectral_window_id": "fsp_1_channels",
        "count": 744,"start": 0,
        "stride": 2,"freq_min": 350000000.0,"freq_max": 368000000.0,
        "link_map": [
        [0, 0],[200, 1],[744, 2],[944, 3]]}, {"spectral_window_id":
        "fsp_2_channels",
        "count": 744,"start": 2000,"stride": 1,"freq_min": 360000000.0,
        "freq_max": 368000000.0,
        "link_map": [[2000, 4],[2200, 5]]}, {"spectral_window_id":
        "zoom_window_1",
        "count": 744,"start": 4000,"stride": 1,"freq_min": 360000000.0,
        "freq_max": 361000000.0,
        "link_map": [[4000, 6],[4200, 7]]}]}, {"channels_id":
          "pulsar_channels",
        "spectral_windows": [{"spectral_window_id": "pulsar_fsp_channels",
        "count": 744,
        "start": 0,"freq_min": 350000000.0,"freq_max": 368000000.0}]}],
        "polarisations": [{"polarisations_id": "all","corr_type":
          ["XX", "XY", "YY", "YX"]}],
        "fields": [{"field_id": "field_a","phase_dir":
        {"ra": [123, 0.1],"dec": [80, 0.1],
        "reference_time": "...","reference_frame": "ICRF3"},
        "pointing_fqdn":
        "low-tmc/telstate/0/pointing"}]},"processing_blocks":
        [{"pb_id": "pb-mvp01-20210623-00000",
        "sbi_ids": ["sbi-mvp01-20200325-00001"],
        "script": {"kind": "realtime",
        "name": "vis_receive","version": "0.1.0"},
        "parameters": {}}, {
        "pb_id": "pb-mvp01-20210623-00001","sbi_ids":
        ["sbi-mvp01-20200325-00001"],
        "script": {"kind": "realtime",
        "name": "test_realtime","version": "0.1.0"},
        "parameters": {}}, {"pb_id":
        "pb-mvp01-20210623-00002","sbi_ids": ["sbi-mvp01-20200325-00002"],
        "script": {"kind": "batch",
        "name": "ical","version": "0.1.0"},"parameters": {},
        "dependencies": [{"pb_id":
        "pb-mvp01-20210623-00000","kind": ["visibilities"]}]
        }, {"pb_id": "pb-mvp01-20210623-00003",
        "sbi_ids": ["sbi-mvp01-20200325-00001",
        "sbi-mvp01-20200325-00002"],"script":
        {"kind": "batch","name": "dpreb","version": "0.1.0"},
        "parameters": {},"dependencies":
          [{"pb_id": "pb-mvp01-20210623-00002",
        "kind": ["calibration"]}]}],"resources":
        {"csp_links": [1, 2, 3, 4],
        "receptors": ["FS4", "FS8", "FS16", "FS17",
        "FS22", "FS23", "FS30", "FS31", "FS32",
        "FS33", "FS36", "FS52", "FS56", "FS57", "FS59",
          "FS62", "FS66", "FS69", "FS70", "FS72",
        "FS73", "FS78", "FS80", "FS88", "FS89", "FS90",
          "FS91", "FS98", "FS108", "FS111", "FS132",
        "FS144", "FS146", "FS158", "FS165", "FS167",
        "FS176", "FS183", "FS193", "FS200", "FS345",
        "FS346", "FS347", "FS348", "FS349", "FS350",
        "FS351", "FS352", "FS353", "FS354", "FS355",
        "FS356", "FS429", "FS430", "FS431", "FS432",
        "FS433", "FS434", "FS465", "FS466", "FS467",
        "FS468", "FS469", "FS470"],"receive_nodes": 10}}}

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

        result_code, message = self.init_adapters()
        if result_code == ResultCode.FAILED:
            return result_code, message

        subarrayID = int(json_argument["subarray_id"])

        result_code, message = self.get_subarray_adapter(subarrayID)
        if result_code == ResultCode.FAILED:
            return result_code, message

        receptor_ids = json_argument["dish"]["receptor_ids"]
        self.logger.debug(f"receptor_ids are:{receptor_ids}")
        for receptor_id in receptor_ids:
            if self.component_manager.is_already_assigned(receptor_id):
                return (
                    ResultCode.FAILED,
                    f"Dish {receptor_id} is already allocated",
                )
            self.logger.info(
                f"Dish {receptor_id} is available for assignment."
            )
        self.component_manager.log_state(
            "Device states before executing AssignResources command"
        )

        self.logger.debug(
            f"Invoking AssignResources command on:{self.tm_subarray_adapter}"
        )

        return_codes, message_or_unique_ids = self.send_command(
            [self.tm_subarray_adapter],
            "Error in calling AssignResources on subarray",
            "AssignResources",
            json.dumps(json_argument),
        )
        for return_code, message_or_unique_id in zip(
            return_codes, message_or_unique_ids
        ):
            if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                return ResultCode.FAILED, message_or_unique_id

            if return_code in [ResultCode.QUEUED, ResultCode.OK]:
                self.component_manager.command_mapping[
                    self.component_manager.command_id
                ] = message_or_unique_id

        self.logger.debug(
            f"Resources assigned successfully to:{self.tm_subarray_adapter}"
        )

        return (ResultCode.OK, "")

    def update_resource_config_file(
        self, json_argument: dict, sdp_id: str
    ) -> None:
        """Updates the resource configuration file.

        :param json_argument: A dictionary containing the JSON argument for
        the update.
        :param id: A string representing the ID for the resource configuration
        file.
        :return: None
        """
        # New type of id "eb_id" is used to distinguish between real
        # SB and id used during testing
        unique_id = self._skuid.fetch_skuid("eb")
        json_argument["sdp"]["execution_block"][sdp_id] = unique_id
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

    def do_low(self, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke AssignResources command on Subarray.

        :param argin: DevString

        Example:

        .. code-block::

        {"interface":"https://schema.skao.int/ska-low-tmc-assignresources/3.0"
        ,"transaction_id":"txn-....-00001","subarray_id":1,
        "mccs":{"subarray_beam_ids":[1],"station_ids":[[1,2]],
        "channel_blocks":[3]},
        "sdp":{"interface":"https://schema.skao.int/ska-sdp-assignres/0.4",
        "execution_block":{"eb_id":"eb-mvp01-20200325-00001",
        "max_length":100,"context":{},"beams":[{"beam_id":"vis0",
        "function":"visibilities"},
        {"beam_id":"pss1","search_beam_id":1,"function":"pulsar search"},
        {"beam_id":"pss2","search_beam_id":2,"function":"pulsar search"},
        {"beam_id":"pst1","timing_beam_id":1,"function":"pulsar timing"},
        {"beam_id":"pst2","timing_beam_id":2,"function":"pulsar timing"},
        {"beam_id":"vlbi1","vlbi_beam_id":1,"function":"vlbi"}],
        "scan_types":[{"scan_type_id":".default","beams":{"vis0":
        {"channels_id":"vis_channels","polarisations_id":"all"},
        "pss1":{"field_id":"pss_field_0","channels_id":"pulsar_channels",
        "polarisations_id":"all"},
        "pss2":{"field_id":"pss_field_1","channels_id":"pulsar_channels",
        "polarisations_id":"all"},
        "pst1":{"field_id":"pst_field_0","channels_id":"pulsar_channels",
        "polarisations_id":"all"},
        "pst2":{"field_id":"pst_field_1","channels_id":"pulsar_channels",
        "polarisations_id":"all"},
        "vlbi":{"field_id":"vlbi_field","channels_id":"vlbi_channels",
        "polarisations_id":"all"}}},
        {"scan_type_id":"target:a","derive_from":".default","beams":
        {"vis0":{"field_id":"field_a"}}}],
        "channels":[{"channels_id":"vis_channels",
        "spectral_windows":[{"spectral_window_id":
        "fsp_1_channels","count":744,"start":0,"stride":2,
        "freq_min":350000000,"freq_max":368000000,
        "link_map":[[0,0],[200,1],[744,2],[944,3]]},
        {"spectral_window_id":"fsp_2_channels",
        "count":744,"start":2000,"stride":1,
        "freq_min":360000000,"freq_max":368000000,
        "link_map":[[2000,4],[2200,5]]},
        {"spectral_window_id":"zoom_window_1","count":744,"start":4000,
        "stride":1,"freq_min":360000000,"freq_max":361000000,
        "link_map":[[4000,6],[4200,7]]}]},
        {"channels_id":"pulsar_channels","spectral_windows":
        [{"spectral_window_id":"pulsar_fsp_channels","count":
        744,"start":0,"freq_min":350000000,"freq_max":368000000}]}],
        "polarisations":[{"polarisations_id":"all","corr_type":
        ["XX","XY","YY","YX"]}],"fields":[{"field_id":"field_a",
        "phase_dir":{"ra":[123,0.1],"dec":[123,0.1],
        "reference_time":"...","reference_frame":"ICRF3"},
        "pointing_fqdn":"low-tmc/telstate/0/pointing"}]},
        "processing_blocks":[{"pb_id":"pb-mvp01-20200325-00001",
        "sbi_ids":["sbi-mvp01-20200325-00001"],"script":{},"parameters":{},
        "dependencies":{}},{"pb_id":"pb-mvp01-20200325-00002",
        "sbi_ids":["sbi-mvp01-20200325-00002"],"script":{},"parameters":{},
        "dependencies":{}},{"pb_id":"pb-mvp01-20200325-00003",
        "sbi_ids":["sbi-mvp01-20200325-00001","sbi-mvp01-20200325-00002"],
        "script":{},
        "parameters":{},"dependencies":{}}],
        "resources":{"csp_links":[1,2,3,4],"receptors":["FS4","FS8"],
        "receive_nodes":10}}}

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

        result_code, message = self.init_adapters()
        if result_code == ResultCode.FAILED:
            return result_code, message

        subarrayID = int(json_argument["subarray_id"])

        result_code, message = self.get_subarray_adapter(subarrayID)
        if result_code == ResultCode.FAILED:
            return result_code, message

        if self.tm_subarray_adapter is None:
            return (
                ResultCode.FAILED,
                ("SubArray Id %s is not existing!", subarrayID),
            )

        try:
            input_mccs_master = self.create_mccs_cmd_data(json_argument)
        except Exception as e:
            return (
                ResultCode.FAILED,
                ("Errors in input json argument: %s", e),
            )

        self.component_manager.log_state(
            "Device states before executing AssignResources command"
        )
        for return_codes, message_or_unique_ids in [
            self.send_command(
                [self.tm_subarray_adapter],
                "Error in calling AssignResources on subarray:"
                + self.tm_subarray_adapter.dev_name,
                "AssignResources",
                json.dumps(json_argument),
            ),
            self.send_command(
                [self.mccs_mln_adapter],
                "Error in calling AssignResources command"
                + " on MCCS Master Leaf Node ",
                "AssignResources",
                json.dumps(input_mccs_master),
            ),
        ]:
            for return_code, message_or_unique_id in zip(
                return_codes, message_or_unique_ids
            ):
                if return_code in [ResultCode.FAILED, ResultCode.REJECTED]:
                    return (
                        ResultCode.FAILED,
                        message_or_unique_id,
                    )
                if return_code in [ResultCode.QUEUED, ResultCode.OK]:
                    if self.component_manager.command_mapping.get(
                        self.component_manager.command_id
                    ):
                        self.logger.info(
                            "Adding the id %s to the command mapping"
                            + "dictionary under command_id: %s",
                            message_or_unique_id,
                            self.component_manager.command_id,
                        )
                        self.component_manager.command_mapping[
                            self.component_manager.command_id
                        ].append(message_or_unique_id)
                    else:
                        self.logger.info(
                            "Creating a command mapping dictionary for id:"
                            + "%s, with unique_id: %s",
                            self.component_manager.command_id,
                            message_or_unique_id,
                        )
                        self.component_manager.command_mapping[
                            self.component_manager.command_id
                        ] = [message_or_unique_id]

        return (ResultCode.OK, "")

    def _validate_low_json(
        self, json_argument: dict, req_keys: List
    ) -> Tuple[bool, str]:
        """Validates the JSON argument for the assign resources command before
            entering the queue.

        :param json_argument: A dictionary
        representing the JSON argument to be validated.
        :param req_keys: A list containing the
        required keys to check in the JSON argument.

        :return: A tuple containing a boolean indicating
        validation success and a string message.
        """
        json_keys = json_argument.keys()
        for key in req_keys:
            if key not in json_keys:
                return (
                    False,
                    f"{key} key is not present in the input json argument.",
                )

        try:
            json_argument["mccs"]["interface"]
        except KeyError:
            return (
                False,
                "JSON Error: Missing 'interface' key in input json arguement",
            )
        try:
            subarray_beams = json_argument["mccs"]["subarray_beams"]
        except KeyError:
            return (
                False,
                "JSON Error: Missing 'subarray_beams' key in input json"
                + " arguement",
            )

        for subarray_beam in subarray_beams:
            try:
                subarray_beam["subarray_beam_id"]
            except KeyError:
                return (
                    False,
                    "JSON Error: Missing 'subarray_beam_id' key in input json"
                    + " arguement.",
                )

            try:
                subarray_beam["apertures"]
            except KeyError:
                return (
                    False,
                    "JSON Error: Missing 'apertures' key in input json"
                    + " arguement.",
                )

            try:
                subarray_beam["number_of_channels"]
            except KeyError:
                return (
                    False,
                    "JSON Error: Missing 'number_of_channels' key in input"
                    + " json arguement",
                )
        return (
            True,
            "The json argument has all the required keys. Validation"
            + " successful.",
        )

    def _validate_and_update_resource_config(
        self, json_argument: dict
    ) -> Tuple[bool, str]:
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
            return False, f"Error while updating SDP schema: {e}"

    def create_mccs_cmd_data(self, json_argument: dict) -> dict:
        """
        Method to prepare the input json_argument required while invoking
        AssignResources()
        command on MCCS Master Leaf Node.
        :param json_argument: The string in JSON format.

        :return: The string in JSON format.
        """
        try:
            subarray_id = json_argument["subarray_id"]
            mccs_input = json_argument["mccs"]
            mccs_input["subarray_id"] = subarray_id
            return mccs_input
        except Exception as e:
            raise Exception("Error while creating MCCS input json") from e

    def get_subarray_adapter(self, subarray_id: int) -> Tuple[ResultCode, str]:
        """Method for obtaining the adapter for a subarray.

        :param subarray_id: An integer representing the subarray ID.
        :return: A tuple containing a ResultCode enum value and a
        string message.
        """
        for adapter in self.subarray_adapters:
            if str(subarray_id) in adapter.dev_name:
                self.tm_subarray_adapter = adapter
                self.component_manager.subarray_devname = adapter.dev_name

        if self.tm_subarray_adapter is None:
            return (
                ResultCode.FAILED,
                f"SubArray Id {subarray_id} is not existing!",
            )

        return ResultCode.OK, ""
