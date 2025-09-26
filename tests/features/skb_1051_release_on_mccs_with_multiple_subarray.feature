@post_deployment @acceptance @SKA_low @new
Scenario: Ability to assgin and release mutltiple subarray
    Given a CentralNode Low device
    And assigned two subarrays to the central node
    When release the resources from both the subarrays
    Then the command is executed successfully on both the subarray_node
    And the command is executed successfully on the mccs master leaf node twice
