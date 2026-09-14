package com.example.hello;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AnimalController {
    public record Animal(int id, String name, String habitat, String diet) {}

    private static final List<Animal> ANIMALS = List.of(
            new Animal(1, "Rode panda", "Bergbos", "Planteneter"),
            new Animal(2, "Zeeotter", "Kustwater", "Vleeseter"),
            new Animal(3, "Olifant", "Savanne", "Planteneter"),
            new Animal(4, "Sneeuwluipaard", "Hooggebergte", "Vleeseter"),
            new Animal(5, "Capibara", "Moeras", "Planteneter"),
            new Animal(6, "Toekan", "Regenwoud", "Alleseter"),
            new Animal(7, "Keizerspinguïn", "Antarctica", "Vleeseter"),
            new Animal(8, "Vos", "Bos", "Alleseter"),
            new Animal(9, "Giraffe", "Savanne", "Planteneter"),
            new Animal(10, "Ringstaartmaki", "Droog bos", "Alleseter"),
            new Animal(11, "Axolotl", "Zoetwater", "Vleeseter"),
            new Animal(12, "Koala", "Eucalyptusbos", "Planteneter"));

    @GetMapping("/api/animals")
    public ResponseEntity<List<Animal>> animals() {
        var selection = new ArrayList<>(ANIMALS);
        Collections.shuffle(selection);
        return ResponseEntity.ok().cacheControl(CacheControl.noStore())
                .body(List.copyOf(selection.subList(0, 6)));
    }
}
