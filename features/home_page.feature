Feature: Orders administration home page

  Scenario: Open the administration home page
    When I visit the home page
    Then I should see the Orders administration page
  
  Scenario: Delete an existing order
    When I visit the home page
    And I enter "1004" as the Order ID
    And I click the Delete Order button
    Then I should see the message "Order 1004 deleted successfully."
