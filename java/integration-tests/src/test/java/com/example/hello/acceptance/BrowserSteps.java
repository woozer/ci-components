package com.example.hello.acceptance;

import java.nio.file.Path;
import java.util.Map;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.BrowserContext;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import com.microsoft.playwright.Response;
import com.microsoft.playwright.Tracing;
import com.microsoft.playwright.options.AriaRole;
import io.cucumber.java.After;
import io.cucumber.java.Before;
import io.cucumber.java.Scenario;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class BrowserSteps {
    private Playwright playwright;
    private Browser browser;
    private BrowserContext context;
    private Page page;
    private JsonNode responseAnimals;

    @Before("@ui")
    public void startBrowser() {
        if (System.getProperty("cucumber.base-url", "").isBlank()) {
            throw new IllegalArgumentException("UI scenarios require -Dcucumber.base-url=http://localhost:8090");
        }
        // The Maven UI profile installs Chromium; do not download unused browsers here.
        playwright = Playwright.create(new Playwright.CreateOptions()
                .setEnv(Map.of("PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD", "1")));
        browser = playwright.chromium().launch();
        context = browser.newContext(new Browser.NewContextOptions().setViewportSize(1280, 1000));
        context.tracing().start(new Tracing.StartOptions().setScreenshots(true).setSnapshots(true));
        page = context.newPage();
    }

    @Given("I use a mobile browser viewport")
    public void mobileViewport() {
        page.setViewportSize(390, 844);
    }

    @When("I open the animal discovery page")
    public void openPage() {
        receiveAnimals(() -> page.navigate(ApplicationHooks.endpoint("/").toString()));
        assertThat(page.getByRole(AriaRole.HEADING, new Page.GetByRoleOptions().setLevel(1)))
                .containsText("bijzondere dieren");
    }

    @When("I request a new animal selection")
    public void refresh() {
        receiveAnimals(() -> page.getByRole(AriaRole.BUTTON, new Page.GetByRoleOptions()
                .setName("Ontdek andere dieren")).click());
    }

    private void receiveAnimals(Runnable action) {
        // response fires when headers arrive; requestfinished includes the full body.
        var request = page.waitForRequestFinished(new Page.WaitForRequestFinishedOptions()
                .setPredicate(candidate -> candidate.url().endsWith("/api/animals")
                        && candidate.method().equals("GET")), action);
        Response response = request.response();
        assertEquals(200, response.status(), "The browser must receive a successful backend response");
        responseAnimals = JsonMapper.builder().build().readTree(response.text());
    }

    @Then("I see {int} animals matching the API response")
    public void assertTable(int count) {
        assertEquals(count, responseAnimals.size());
        var rows = page.locator("tbody tr");
        assertThat(rows).hasCount(count);
        for (int i = 0; i < count; i++) {
            var animal = responseAnimals.get(i);
            assertThat(rows.nth(i).getByRole(AriaRole.ROWHEADER)).hasText(animal.path("name").asString());
            assertThat(rows.nth(i).getByRole(AriaRole.CELL).nth(0)).hasText(animal.path("habitat").asString());
            assertThat(rows.nth(i).getByRole(AriaRole.CELL).nth(1)).hasText(animal.path("diet").asString());
        }
        assertThat(page.getByRole(AriaRole.BUTTON)).isEnabled();
        assertThat(page.getByRole(AriaRole.ALERT)).hasCount(0);
    }

    @Then("the page fits the viewport")
    public void assertViewport() {
        assertTrue((Boolean) page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"));
    }

    @After("@ui")
    public void closeBrowser(Scenario scenario) {
        try {
            if (page != null && !page.isClosed()) {
                // Attach the final browser state to the ordinary Cucumber HTML report.
                scenario.attach(page.screenshot(new Page.ScreenshotOptions().setFullPage(true)),
                        "image/png", "Browser result");
            }
            if (context != null) {
                var options = new Tracing.StopOptions();
                if (scenario.isFailed()) {
                    options.setPath(Path.of("target/cucumber/trace-" + java.util.UUID.randomUUID() + ".zip"));
                }
                context.tracing().stop(options);
            }
        } finally {
            try {
                if (browser != null) browser.close();
            } finally {
                if (playwright != null) playwright.close();
            }
        }
    }
}
