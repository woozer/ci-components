package com.example.hello;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class HelloControllerTest {
    @Test
    void returnsGreeting() {
        assertEquals("hello world", new HelloController().hello());
    }
}
