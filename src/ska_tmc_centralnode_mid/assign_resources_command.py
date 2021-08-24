"""
AssignResources class for CentralNode.
"""
import json
import ast
import os
# Tango imports
import tango
from tango import DevState, DevFailed
from ska.base.commands import BaseCommand
from tmc.common.tango_client import TangoClient
from tmc.common.tango_server_helper import TangoServerHelper
from ska_tmc_centralnode_mid import const
from ska_tmc_centralnode_mid.receptor_reassignment_checker import ReceptorReassignmentChecker
from ska_tmc_centralnode_mid.input_validator import AssignResourceValidator
from ska_tmc_centralnode_mid.device_data import DeviceData
from ska_tmc_centralnode_mid.exceptions import ResourceReassignmentError, ResourceNotPresentError
from ska_tmc_centralnode_mid.exceptions import SubarrayNotPresentError, InvalidJSONError
from ska_ser_skuid.client import SkuidClient

class AssignResources(BaseCommand):
    """
    A class for CentralNode's AssignResources() command.

    Assigns resources to given subarray. It accepts the subarray id, receptor id list and SDP block in JSON
    string format. Upon successful execution, the 'receptor_ids' attribute of the given subarray is populated
    with the given receptors.Also checking for duplicate allocation of resources is done. If already allocated
    it will throw error message regarding the prior existence of resource.
    """

    def check_allowed(self):
        """
        Checks whether this command is allowed to be run in current device state

        :return: True if this command is allowed to be run in current device state

        :rtype: boolean

        :raises: DevFailed if this command is not allowed to be run
            in current device state

        """

        if self.state_model.op_state in [
            DevState.FAULT,
            DevState.UNKNOWN,
            DevState.DISABLE,
        ]:
            tango.Except.throw_exception(
                f"Command AssignResources is not allowed in current state {self.state_model.op_state}.",
                "Failed to invoke AssignResources command on CentralNode.",
                "CentralNode.AssignResources()",
                tango.ErrSeverity.ERR,
            )
        return True

    def do(self, argin):
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

        raises:
            DevFailed when the API fails to allocate resources.

        """
        device_data = DeviceData.get_instance()
        device_data.receptor_ids = []
        argout = []

        ## Validate the input JSON string.

        this_server = TangoServerHelper.get_instance()
        self.tm_mid_subarrays = this_server.read_property("TMMidSubarrayNodes")
        self.dln_prefix = this_server.read_property("DishLeafNodePrefix")[0]
        try:
            # TODO: Uncomment this code when CDM library will be aligned as per ADR-35
            # self.logger.info("Validating input string.")
            # input_validator = AssignResourceValidator(
            #     self.tm_mid_subarrays,
            #     device_data._dish_leaf_node_devices,
            #     self.dln_prefix,
            #     self.logger,
            # )
            # json_argument = input_validator.loads(argin)
            json_argument= json.loads(argin)

            sdp_keys = list(json_argument["sdp"].keys())
            print("sdp keys are:::::::::::::::::::::::::::::::", sdp_keys)
            sdp_values = list(json_argument["sdp"].values())
            print("sdp keys are:::::::::::::::::::::::::::::::", sdp_values)
            if "" in sdp_values:
                id = sdp_keys[sdp_values.index("")]
                print("id is::::::::::::::::::::::::::::::::::::::::::", id)
                self.update_resource_config_file(json_argument, id)

            # if not json_argument["sdp"][sdp_keys[1]]:
            #     self.update_resource_config_file(json_argument, sd)
            # if json_argument["sdp"]["eb_id"]:
            #     if json_argument["sdp"]["eb_id"] == "":
            #         self.update_resource_config_file(json_argument)
            # elif json_argument["sdp"]["sb_id"]:
            #     if json_argument["sdp"]["sb_id"] == "":
            #         self.update_resource_config_file(json_argument)
            # else:
            #     self.logger.info("No eb id or sb id are present in SDP block of AssignResources input json string.")

            # Create subarray proxy
            if 'transaction_id' in json_argument:
                del json_argument["transaction_id"]
            subarrayID = int(json_argument["subarray_id"])
            subarrayFqdn = device_data.subarray_FQDN_dict[subarrayID]
            ## check for duplicate allocation
            self.logger.info("Checking for resource reallocation.")
            if device_data.check_resources is None:
                device_data.check_resources = ReceptorReassignmentChecker(self.logger)
            device_data.check_resources.do(json_argument["dish"]["receptor_ids"])

            # Allocate resources to subarray
            # Remove Subarray Id key from input json argument and send the json with
            # receptor Id list and SDP block to TMC Subarray Node
            self.logger.info("Allocating resource to subarray %d", subarrayID)
            input_json_subarray = json_argument.copy()
            input_to_sa = json.dumps(input_json_subarray)
            subarray_client = TangoClient(subarrayFqdn)

            resources_allocated_return = subarray_client.send_command(
                const.CMD_ASSIGN_RESOURCES, input_to_sa
            )

            # Note: resources_allocated_return[1] contains the JSON string containing
            # allocated resources.
            # resources_allocated = resources_allocated_return[1]
            log_msg = f"Return value from subarray node:{resources_allocated_return}" 
            self.logger.info(log_msg)
            resources_allocated = ast.literal_eval(resources_allocated_return[1][0])
            log_msg = f"resources_assigned:{resources_allocated}"
            self.logger.debug(log_msg)
            device_data.resource_manager.update_resource_matrix(
                resources_allocated, subarrayID
            )

            # Allocation successful
            this_server.write_attr("activityMessage", const.STR_ASSIGN_RESOURCES_SUCCESS, False)
            self.logger.debug(const.STR_ASSIGN_RESOURCES_SUCCESS)

            # Prepare output argument
            argout = {"dish": {"receptor_ids_allocated": device_data.receptor_ids}}
            self.logger.debug(argout)
        except (
            InvalidJSONError,
            ResourceNotPresentError,
            SubarrayNotPresentError,
        ) as error:
            self.logger.exception("Exception in AssignResource(): %s", str(error))
            this_server.write_attr("activityMessage", f"Exception in validating input:{error}", False)

            log_msg = f"{const.STR_ASSIGN_RES_EXEC}{error}"
            self.logger.exception(error)
            tango.Except.throw_exception(
                const.STR_RESOURCE_ALLOCATION_FAILED,
                log_msg,
                "CentralNode.AssignResourcesCommand",
                tango.ErrSeverity.ERR,
            )

        except ResourceReassignmentError as resource_error:
            self.logger.exception(
                "List of the dishes that are already allocated: %s",
                str(resource_error.resources_reallocation),
            )
            this_server.write_attr("activityMessage", f"{const.STR_DISH_DUPLICATE}{resource_error.resources_reallocation}", False)

            log_msg = f"{const.STR_DISH_DUPLICATE}{resource_error}"
            self.logger.exception(resource_error)
            tango.Except.throw_exception(
                const.STR_RESOURCE_ALLOCATION_FAILED,
                log_msg,
                "CentralNode.AssignResourcesCommand",
                tango.ErrSeverity.ERR,
            )
        except ValueError as ve:
            self.logger.exception("Exception in AssignResources command: %s", str(ve))
            this_server.write_attr("activityMessage", f"Invalid value in input:{ve}", False)

            log_msg = f"{const.STR_ASSIGN_RES_EXEC}{ve}"    
            self.logger.exception(ve)
            tango.Except.throw_exception(
                const.STR_RESOURCE_ALLOCATION_FAILED,
                log_msg,
                "CentralNode.AssignResourcesCommand",
                tango.ErrSeverity.ERR,
            )
        except DevFailed as dev_failed:
            log_msg = f"{const.ERR_ASSGN_RESOURCES}{dev_failed}"
            self.logger.exception(dev_failed)
            tango.Except.throw_exception(
                const.STR_CMD_FAILED,
                log_msg,
                "CentralNode.AssignResourcesCommand",
                tango.ErrSeverity.ERR,
            )
        message = json.dumps(argout)
        self.logger.info(message)
        return message

    def update_resource_config_file(self, json_argument, id):
        '''This method utilizes SKUID service to generate unique sb_id / eb_id and pb_id'''
        # Here, 'ska-ser-skuid-test-svc.tmcmid.svc.cluster.local:9870' is fixed URL to access SKUID service running on port 9870
        client = SkuidClient('ska-ser-skuid-test-svc.tmcmid.svc.cluster.local:9870')
        # New type of id "eb_id" is used to distinguish between real SB and id used during testing
        unique_id = client.fetch_skuid("eb")
        json_argument["sdp"][id] = unique_id
        if "processing_blocks" in json_argument["sdp"]:
            for i in range(len(json_argument["sdp"]["processing_blocks"])):
                pb_id = client.fetch_skuid("pb")
                json_argument["sdp"]["processing_blocks"][i]["pb_id"] = pb_id
                if "dependencies" in json_argument["sdp"]["processing_blocks"][i]:
                    if i == 0:
                        json_argument["sdp"]["processing_blocks"][i]["dependencies"][0]["pb_id"] = \
                            json_argument["sdp"]["processing_blocks"][i]["pb_id"]
                    else:
                        json_argument["sdp"]["processing_blocks"][i]["dependencies"][0]["pb_id"] = \
                            json_argument["sdp"]["processing_blocks"][i - 1]["pb_id"]
        print("json arg is:::::::::::::::::::::::::::::::::::::::::::", json_argument)

        # PROTECTED REGION END #    //  CentralNode.AssignResources
