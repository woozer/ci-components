Feature: Discover animals
  @smoke @animals
  Scenario: Retrieve a random selection of animals
    When I send a GET request to "/api/animals"
    Then the response status is 200
    And the response contains 6 unique animals with a name, habitat and diet
