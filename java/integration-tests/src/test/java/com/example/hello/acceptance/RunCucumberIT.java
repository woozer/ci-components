package com.example.hello.acceptance;

import org.junit.platform.suite.api.ConfigurationParameter;
import org.junit.platform.suite.api.IncludeEngines;
import org.junit.platform.suite.api.SelectPackages;
import org.junit.platform.suite.api.Suite;

@Suite(failIfNoTests = true)
@IncludeEngines("cucumber")
@SelectPackages("features")
@ConfigurationParameter(key = "cucumber.glue", value = "com.example.hello.acceptance")
@ConfigurationParameter(key = "cucumber.plugin", value = "pretty,json:target/cucumber/cucumber.json,html:target/cucumber/cucumber.html")
@ConfigurationParameter(key = "cucumber.junit-platform.naming-strategy", value = "long")
public class RunCucumberIT {
}
