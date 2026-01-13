package springbootApplication.controller;

import springbootApplication.domain.Timer;
import springbootApplication.service.TimerService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/timers")
@Tag(name = "Timers", description = "CRUD operations for timers")
public class TimerController {

    private final TimerService timerService;

    public TimerController(TimerService timerService) {
        this.timerService = timerService;
    }

    @GetMapping
    @Operation(summary = "Get all timers")
    public ResponseEntity<List<Timer>> getAllTimers() {
        List<Timer> timers = timerService.getAllTimers();
        if (timers.isEmpty()) {
            return ResponseEntity.noContent().build();
        }
        return ResponseEntity.ok(timers);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get a timer by ID")
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "Timer found"),
        @ApiResponse(responseCode = "404", description = "Timer not found")
    })
    public ResponseEntity<Timer> getTimerById(@PathVariable Long id) {
        return timerService.getTimerById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    @Operation(summary = "Create a new timer")
    public ResponseEntity<Timer> createTimer(@RequestBody Timer timer) {
        Timer createdTimer = timerService.createTimer(timer);
        return ResponseEntity.status(HttpStatus.CREATED).body(createdTimer);
    }


    @DeleteMapping("/{id}")
    @Operation(summary = "Delete a timer by ID")
    public ResponseEntity<Void> deleteTimer(@PathVariable Long id) {
        timerService.deleteTimer(id);
        return ResponseEntity.noContent().build();
    }
}
