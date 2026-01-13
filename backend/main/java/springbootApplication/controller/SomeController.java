package springbootApplication.controller;

import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.GetMapping;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

@RestController
@Tag(name = "Sample", description = "샘플 엔드포인트")
public class SomeController {

    @GetMapping("/some-endpoint")
    @Operation(summary = "샘플 메서드", description = "간단한 Hello World 메시지 반환")
    public String someMethod() {
        return "Hello, World!";
    }
}