Feature: Cancel an Order
  As an administrator
  I need a Cancel button on the admin page
  So that I can cancel an order without deleting it

  Background:
    Given the following orders
      | customer_id | status  |
      | 201         | pending |
      | 202         | shipped |

  Scenario: Cancel a pending Order
    Given the "pending" order is shown in the form
    When I click the Cancel Order button
    Then I should see "cancelled successfully." in the results message
    And I should see the status "cancelled"

  Scenario: Cancel an Order that cannot be cancelled
    Given the "shipped" order is shown in the form
    When I click the Cancel Order button
    Then I should see "cannot be cancelled" in the results message
    And I should see the status "shipped"
