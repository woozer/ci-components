@ui
Feature: Explore animals in the browser
  Background:
    When I send a GET request to "/healthz"
    Then the response status is 200

  @smoke
  Scenario: Discover and refresh animals from the backend
    When I open the animal discovery page
    Then I see 6 animals matching the API response
    When I request a new animal selection
    Then I see 6 animals matching the API response

  Scenario: Keep the animal table usable on a small screen
    Given I use a mobile browser viewport
    When I open the animal discovery page
    Then I see 6 animals matching the API response
    And the page fits the viewport
