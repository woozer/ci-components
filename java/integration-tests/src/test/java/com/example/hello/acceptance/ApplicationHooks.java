package com.example.hello.acceptance;

import java.net.URI;

import com.example.hello.HelloApplication;
import io.cucumber.java.AfterAll;
import io.cucumber.java.BeforeAll;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;

public final class ApplicationHooks {
    private static ConfigurableApplicationContext application;
    private static URI baseUri;

    @BeforeAll
    public static void startApplication() {
        String configuredUrl = System.getProperty("cucumber.base-url", "").strip();
        if (!configuredUrl.isEmpty()) {
            baseUri = URI.create(configuredUrl.endsWith("/") ? configuredUrl : configuredUrl + "/");
            if (!("http".equals(baseUri.getScheme()) || "https".equals(baseUri.getScheme()))
                    || baseUri.getHost() == null || baseUri.getQuery() != null || baseUri.getFragment() != null) {
                throw new IllegalArgumentException("cucumber.base-url must be an absolute HTTP(S) URL without a query or fragment");
            }
            return;
        }

        application = SpringApplication.run(HelloApplication.class,
                "--server.address=127.0.0.1", "--server.port=0");
        String port = application.getEnvironment().getRequiredProperty("local.server.port");
        baseUri = URI.create("http://127.0.0.1:" + port + "/");
    }

    static URI endpoint(String path) {
        return baseUri.resolve(path.startsWith("/") ? path.substring(1) : path);
    }

    @AfterAll
    public static void stopApplication() {
        if (application != null) {
            application.close();
            application = null;
        }
    }
}
