package com.example.hello.acceptance;

import java.io.IOException;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.HashSet;

import tools.jackson.databind.json.JsonMapper;

import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class HelloSteps {
    private HttpResponse<String> response;

    @When("I send a GET request to {string}")
    public void sendGet(String path) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder(ApplicationHooks.endpoint(path))
                .timeout(Duration.ofSeconds(10))
                .GET()
                .build();
        try (HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build()) {
            response = client.send(request, HttpResponse.BodyHandlers.ofString());
        }
    }

    @Then("the response status is {int}")
    public void assertStatus(int expected) {
        assertEquals(expected, response.statusCode());
    }

    @Then("the response message is {string}")
    public void assertMessage(String expected) {
        assertEquals(expected, response.body());
    }

    @Then("the response content type is plain text")
    public void assertPlainText() {
        String contentType = response.headers().firstValue("Content-Type").orElse("");
        assertTrue(contentType.equals("text/plain") || contentType.startsWith("text/plain;"),
                "Expected text/plain but received " + contentType);
    }

    @Then("the health status is {string}")
    public void assertHealth(String expected) {
        assertTrue(response.headers().firstValue("Content-Type").orElse("").contains("json"));
        var health = JsonMapper.builder().build().readTree(response.body());
        assertEquals(expected, health.path("status").asString());
    }

    @Then("the response contains {int} unique animals with a name, habitat and diet")
    public void assertAnimals(int count) {
        assertTrue(response.headers().firstValue("Content-Type").orElse("").startsWith("application/json"));
        var animals = JsonMapper.builder().build().readTree(response.body());
        assertTrue(animals.isArray(), "Expected an array of animals");
        assertEquals(count, animals.size());
        var ids = new HashSet<Integer>();
        for (var animal : animals) {
            assertTrue(animal.path("id").isIntegralNumber());
            assertTrue(animal.path("id").asInt() > 0);
            assertTrue(ids.add(animal.path("id").asInt()), "Duplicate animal ID");
            for (var field : new String[]{"name", "habitat", "diet"}) {
                assertTrue(animal.path(field).isString());
                assertTrue(!animal.path(field).asString().isBlank(), "Missing " + field);
            }
        }
        assertTrue(response.headers().firstValue("Cache-Control").orElse("").contains("no-store"));
    }
}
