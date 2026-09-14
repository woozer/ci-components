Feature: Hello World REST endpoint
  Clients receive a greeting from the running application.

  @smoke
  Scenario: Retrieve the greeting
    When I send a GET request to "/hello"
    Then the response status is 200
    And the response message is "hello world"
    And the response content type is plain text

  Scenario: Unknown endpoints return not found
    When I send a GET request to "/does-not-exist"
    Then the response status is 404

  @smoke
  Scenario Outline: The backend reports its health
    When I send a GET request to "<endpoint>"
    Then the response status is 200
    And the health status is "UP"

    Examples:
      | endpoint                    |
      | /actuator/health            |
      | /actuator/health/readiness  |
      | /actuator/health/liveness   |
