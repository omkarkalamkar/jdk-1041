"""
AssignResources Command class for CentralNode.
"""
import json
import time
from typing import Optional, Tuple

from ska_ser_skuid.client import SkuidClient
from ska_tango_base.base import TaskCallbackType
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_base.executor import TaskStatus
from ska_tmc_common import AdapterFactory, TimeKeeper, TimeoutCallback
from ska_tmc_common.v1.error_propagation_tracker import (
    error_propagation_tracker,
)
from ska_tmc_common.v1.timeout_tracker import timeout_tracker

from ska_tmc_centralnode.commands.central_node_command import (
    AssignReleaseResources,
)


class AssignResources(AssignReleaseResources):
    """
    A class for CentralNode's AssignResources() command.

    Assigns resources to a given subarray. It accepts the subarray ID,
    receptor ID list, and SDP block in JSON string format.

    Upon successful execution, the 'receptor_ids' attribute of the given
    subarray is populated with the given receptors.

    Checking for duplicate allocation of resources is done.
    If already allocated, it will throw an error message regarding the prior
    existence of the resource.
    """

    # pylint:disable=keyword-arg-before-vararg
    def __init__(
        self,
        component_manager,
        adapter_factory=None,
        skuid=SkuidClient(
            "ska-ser-skuid-test-svc.ska-tmc-centralnode.svc.techops.internal"
            + ".skao.int:9870"
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
        self.timekeeper = TimeKeeper(
            self.component_manager.command_timeout, logger
        )

        self.timeout_id = f"{time.time()}_{__class__.__name__}"
        self.timeout_callback = TimeoutCallback(self.timeout_id, self.logger)
        self.task_callback: TaskCallbackType

    @timeout_tracker
    @error_propagation_tracker(
        "get_subarray_obsstate", [ObsState.RESOURCING, ObsState.IDLE]
    )
    def assign_resources(
        self,
        argin: str,
    ) -> Tuple[ResultCode, str]:
        """
        This is a long running command method for AssignResources command.

        It executes the do hook and invokes the AssignResources command on
        lower-level devices.

        :param argin: Input argument for the command.
        :type argin: str

        :returns: Result code and message.
        :rtype: Tuple[ResultCode, str]
        """
        return self.do(argin)

    def update_task_status(
        self, result: Tuple[ResultCode, str], exception: str = ""
    ) -> None:
        """
        Updates the task status for a command.

        Parameters:
        -----------
        result : Tuple[ResultCode, str]
            A tuple containing the result code and a message.
            The result code indicates whether the command succeeded or failed.
        exception : str, optional
            A string representing any exception message.
            This is used when the result indicates a failure.
            Default is an empty string.

        Returns:
        --------
        None
        """
        if result[0] == ResultCode.FAILED:
            self.task_callback(
                result=result, status=TaskStatus.COMPLETED, exception=exception
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

    # pylint:disable=signature-differs
    def do_mid(self, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke the AssignResources command on a Subarray.

        :param argin: Input argument for the command
        :type argin: str

        {"interface": "https://schema.skao.int/ska-tmc-assignresources/2.1",
        "transaction_id": "txn-....-00001","subarray_id": 1,"dish": {
        "receptor_ids": ["SKA001"] },"sdp": {
        "interface": "https://schema.skao.int/ska-sdp-assignres/0.4",
        "execution_block": {"eb_id": "eb-mvp01-20210623-00000",
        "max_length": 100.0,"context": {},"beams": [{ "beam_id": "vis0",
        "function": "visibilities"}, {"beam_id": "pss1","search_beam_id": 1,
        "function": "pulsar search"}, {"beam_id": "pss2", "search_beam_id": 2,
        "function": "pulsar search"}, {"beam_id": "pst1","timing_beam_id": 1,
        "function": "pulsar timing"}, {"beam_id": "pst2","timing_beam_id": 2,
        "function": "pulsar timing"}, {"beam_id": "vlbi1",vlbi_beam_id": 1,
        function": "vlbi"}],"scan_types": [{"scan_type_id": ".default",
        "beams": {"vis0": {"channels_id": "vis_channels",
        "polarisations_id": "all"},"pss1": {"field_id": "pss_field_0",
        "channels_id": "pulsar_channels","polarisations_id": "all"  },
        "pss2": {"field_id": "pss_field_1","channels_id": "pulsar_channels",
        "polarisations_id": "all"},"pst1": {"field_id": "pst_field_0",
        "channels_id": "pulsar_channels","polarisations_id": "all"},
        "pst2": {"field_id": "pst_field_1","channels_id": "pulsar_channels",
        "polarisations_id": "all"},"vlbi": {"field_id": "vlbi_field",
        "channels_id": "vlbi_channels","polarisations_id": "all"}}}, {
        "scan_type_id": "target:a","derive_from": ".default","beams": {
        "vis0": {"field_id": "field_a"}}}],"channels": [{
        "channels_id": "vis_channels","spectral_windows": [{
        "spectral_window_id": "fsp_1_channels","count": 744,"start": 0,
        "stride": 2,"freq_min": 350000000.0,"freq_max": 368000000.0,
        "link_map": [[0, 0],[200, 1],[744, 2],[944, 3]]}, {
        "spectral_window_id": "fsp_2_channels","count": 744,"start": 2000,
        "stride": 1,"freq_min": 360000000.0,"freq_max": 368000000.0,
        "link_map": [ [2000, 4],[2200, 5]]}, {
        "spectral_window_id": "zoom_window_1","count": 744,"start": 4000,
        "stride": 1,"freq_min": 360000000.0,"freq_max": 361000000.0,
        "link_map": [[4000, 6],[4200, 7]]}]}, {"channels_id": "pulsar_channels"
        "spectral_windows": [{"spectral_window_id": "pulsar_fsp_channels",
        "count": 744,"start": 0,"freq_min": 350000000.0,"freq_max": 368000000.0
        }]}],"polarisations": [{"polarisations_id": "all",
        "corr_type": ["XX", "XY", "YY", "YX"]}],
        "fields": [{"field_id": "field_a","phase_dir": {"ra": [123, 0.1],
        "dec": [80, 0.1],"reference_time": "...","reference_frame": "ICRF3"},
        "pointing_fqdn": "low-tmc/telstate/0/pointing"}]},
        "processing_blocks": [{"pb_id": "pb-mvp01-20210623-00000",
        "sbi_ids": ["sbi-mvp01-20200325-00001"],"script": {"kind": "realtime",
        "name": "vis_receive","version": "0.1.0"},"parameters": {}}, {
        "pb_id": "pb-mvp01-20210623-00001",
        "sbi_ids": ["sbi-mvp01-20200325-00001"],
        "script": {"kind": "realtime","name": "test_realtime",
        "version": "0.1.0"},"parameters": {}}, {
        "pb_id": "pb-mvp01-20210623-00002",
        "sbi_ids": ["sbi-mvp01-20200325-00002"],"script": {"kind": "batch",
        "name": "ical","version": "0.1.0"},"parameters": {},"dependencies": [{
        "pb_id": "pb-mvp01-20210623-00000","kind": ["visibilities"]}]}, {
        "pb_id": "pb-mvp01-20210623-00003",
        "sbi_ids": ["sbi-mvp01-20200325-00001", "sbi-mvp01-20200325-00002"],
        "script": {"kind": "batch","name": "dpreb","version": "0.1.0" },
        "parameters": {},"dependencies": [{"pb_id": "pb-mvp01-20210623-00002",
        "kind": ["calibration"]}]}],
        "resources": {"csp_links": [1, 2, 3, 4],
        "receptors": ["FS4", "FS8", "FS16", "FS17", "FS22", "FS23", "FS30",
        "FS31", "FS32", "FS33", "FS36", "FS52", "FS56", "FS57", "FS59", "FS62",
        "FS66", "FS69", "FS70", "FS72", "FS73", "FS78", "FS80", "FS88",
        "FS89", "FS90", "FS91", "FS98", "FS108", "FS111", "FS132", "FS144",
        "FS146", "FS158", "FS165", "FS167", "FS176", "FS183", "FS193",
        "FS200", "FS345", "FS346", "FS347", "FS348", "FS349", "FS350",
        "FS351", "FS352", "FS353", "FS354", "FS355", "FS356",
        "FS429", "FS430", "FS431", "FS432", "FS433", "FS434",
        "FS465", "FS466", "FS467", "FS468", "FS469", "FS470"],
        "receive_nodes": 10 } }}

        :returns: Result code and message
        :rtype: Tuple[ResultCode, str]
        """
        try:
            self.logger.debug("Loading the JSON string: %s", argin)
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
        self.logger.debug(f"Receptor IDs are: {receptor_ids}")
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

        self.logger.info(
            f"Resources assigned successfully to:{self.tm_subarray_adapter}"
        )

        return (ResultCode.OK, "")

    def update_resource_config_file(
        self, json_argument: dict, sdp_id: str
    ) -> None:
        """
        Updates the resource configuration file.

        This method updates the resource configuration file with unique
        identifiers for execution blocks and processing blocks.
        It fetches unique IDs using the `skuid` service and updates the
        corresponding entries in the provided JSON argument.

        Parameters:
        -----------
        json_argument : dict
            A dictionary containing the JSON argument for the update.
            This dictionary should have a specific structure
            with keys for 'sdp', 'execution_block', and 'processing_blocks'.
        sdp_id : str
            A string representing the ID for the resource configuration file.

        Returns:
        --------
        None

        Raises:
        -------
        Exception
            If the 'processing_blocks' key is not present in the input
            JSON argument.
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

    # pylint:disable=signature-differs
    def do_low(self, argin: str) -> Tuple[ResultCode, str]:
        """
        Method to invoke AssignResources command on Subarray.

        :param argin: DevString

        Example:

        .. code-block::

        {'interface':
            'https://schema.skao.int/ska-low-tmc-assignresources/4.0',
            'transaction_id': 'txn-....-00001', 'subarray_id': 1, 'mccs':
            {'interface':
            'https://schema.skao.int/ska-low-mccs-controller-allocate/3.0',
            'subarray_beams': [{'subarray_beam_id': 1, 'apertures':
            [{'station_id': 1, 'aperture_id': 'AP001.01'},
            {'station_id': 1, 'aperture_id': 'AP001.02'}, {'station_id': 2,
            'aperture_id': 'AP002.01'}, {'station_id': 2, 'aperture_id':
              'AP002.02'}
            ], 'number_of_channels': 8}]}, 'csp': {'pss': {'pss_beam_ids':
            [1, 2, 3]}, 'pst': {'pst_beam_ids': [1]}}, 'sdp': {'interface': '
            https://schema.skao.int/ska-sdp-assignres/0.4', 'resources': {'r
            eceptors': ['C4', 'C57', 'C108', 'C165', 'C193', 'C200', 'S8-1',
              'S8-2', 'S9-1', 'S9-5', 'S10-1', 'S10-6', 'S16-3', 'S16-4',
              'S16-6'], 'receive_nodes': 1}, 'execution_block': {'eb_id':
              'eb-test-20220916-00000', 'context': {}, 'max_length': 3600.0,
              'beams': [{'beam_id': 'vis0', 'function': 'visibilities'}],
              'scan_types': [{'scan_type_id': '.default', 'beams':
              {'vis0': {'channels_id': 'vis_channels', 'polarisations_id':
              'all'}}}, {'scan_type_id': 'target:a', 'derive_from':
              '.default', 'beams': {'vis0': {'field_id': 'field_a'}}},
              {'scan_type_id': 'calibration:b', 'derive_from': '.default',
            'beams': {'vis0': {'field_id': 'field_b'}}}], 'channels':
            [{'channels_id': 'vis_channels', 'spectral_windows':
              [{'spectral_window_id': 'fsp_1_channels', 'count': 4,
              'start': 0, 'stride': 2, 'freq_min': 350000000.0, 'freq_max':
             368000000.0, 'link_map': [[0, 0], [200, 1], [744, 2],
             [944, 3]]}]}], 'polarisations': [{'polarisations_id':
             'all', 'corr_type': ['XX', 'XY', 'YX', 'YY']}], 'fields':
            [{'field_id': 'field_a', 'phase_dir': {'ra': [123.0],
            'dec': [-60.0], 'reference_time': '...', 'reference_frame':
            'ICRF3'}, 'pointing_fqdn': '...'}, {'field_id': 'field_b',
            'phase_dir': {'ra': [123.0], 'dec': [-60.0], 'reference_time':
            '...', 'reference_frame': 'ICRF3'}, 'pointing_fqdn': '...'}]},
            'processing_blocks': [{'pb_id': 'pb-test-20220916-00000',
            'script': {'kind': 'realtime', 'name': 'test-receive-addresses',
            'version': '0.7.1'}, 'sbi_ids': ['sbi-mvp01-20210623-00000'],
            'parameters': {}}]}}

        :return: A tuple containing a return code and a string msg.
            For Example:
            (ResultCode.OK, "")

        :raises:
            KeyError if input argument json string contains invalid key

            ValueError if input argument json string contains invalid value

            AssertionError if  Mccs On command is not completed.

        """
        try:
            json_argument = json.loads(argin)
            self.logger.debug(
                "Executing AssignResources command with arguments: %s",
                json_argument,
            )
        except Exception as exception:
            return (
                ResultCode.FAILED,
                ("Problem in loading the JSON string: %s", exception),
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
        except Exception as exception:
            return (
                ResultCode.FAILED,
                ("JSON arguments error:: %s", exception),
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

    def _validate_and_update_resource_config(
        self, json_argument: dict
    ) -> Tuple[bool, str]:
        """
        Validate and update the resource configuration.

        This method validates if the 'eb_id' is present in the SDP schema
        within the provided JSON argument. If the 'eb_id' is not
        present, it fetches the appropriate IDs and updates the resource
        configuration file accordingly.

        Parameters:
        -----------
        json_argument : dict
            A dictionary representing the low-level JSON configuration for the
            resource.

        Returns:
        --------
        Tuple[bool, str]
            A tuple where the first element is a boolean indicating the success
            of the validation and update process, and the second
            element is a string containing an error message if the
            process failed.

        Raises:
        -------
        Exception
            If an error occurs while updating the SDP schema, it returns
            a tuple
            with False and the error message.
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
        except Exception as exception:
            return False, f"Error while updating SDP schema: {exception}"

    def create_mccs_cmd_data(self, json_argument: dict) -> dict:
        """
        Method to prepare the input json_argument required while invoking
        AssignResources() command on MCCS Master Leaf Node.

        :param: json_argument
        :type: The string in JSON format.

        :return: The string in JSON format.
        """
        try:
            subarray_id = json_argument["subarray_id"]
            mccs_input = json_argument["mccs"]
            mccs_input["subarray_id"] = subarray_id
            return mccs_input
        except Exception as exception:
            raise Exception(
                "Error while creating MCCS input json"
            ) from exception

    def get_subarray_adapter(self, subarray_id: int) -> Tuple[ResultCode, str]:
        """Method for obtaining the adapter for a subarray.

        :param: subarray_id
        :type: An integer representing the subarray ID.
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
