Feature: Query Orders by status
  As an eCommerce administrator
  I need to filter Orders by status in the administration UI
  So that I can quickly view Orders in a specific stage of processing

  Background:
    Given the following orders
      | customer_id | status    |
      | 101         | pending   |
      | 102         | shipped   |
      | 103         | pending   |
      | 104         | delivered |

  Scenario: Filter Orders by status
    When I visit the home page
    And I select "pending" in the Status filter
    And I click the Search Orders button
    Then I should see the search message "2 order(s) found."
    And I should see 2 orders in the search results
    And I should only see orders with status "pending" in the search results

  Scenario: No Orders match the status
    When I visit the home page
    And I select "processing" in the Status filter
    And I click the Search Orders button
    Then I should see the search message "No orders found."
    And I should see 0 orders in the search results
