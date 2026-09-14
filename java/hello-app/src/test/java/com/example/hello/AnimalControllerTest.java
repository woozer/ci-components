package com.example.hello;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class AnimalControllerTest {
    private final AnimalController controller = new AnimalController();

    @Test
    void returnsSixDistinctAnimalsWithDisplayFields() {
        var response = controller.animals();
        var animals = response.getBody();

        assertEquals(200, response.getStatusCode().value());
        assertNotNull(animals);
        assertEquals(6, animals.size());
        assertEquals(6, animals.stream().map(AnimalController.Animal::id).distinct().count());
        assertTrue(animals.stream().allMatch(animal -> animal.id() > 0
                && !animal.name().isBlank() && !animal.habitat().isBlank() && !animal.diet().isBlank()));
    }

    @Test
    void preventsCachingAndProtectsPreviousSelections() {
        var first = controller.animals();
        var animals = first.getBody();
        assertEquals("no-store", first.getHeaders().getCacheControl());
        assertNotNull(animals);
        var snapshot = java.util.List.copyOf(animals);
        controller.animals();
        assertEquals(snapshot, animals);
        assertThrows(UnsupportedOperationException.class, () -> animals.clear());
    }
}
