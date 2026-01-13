package springbootApplication.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.util.ArrayList;
import java.util.List;

@Entity
@Getter
@Setter
@Table(name = "recipe_steps")
public class RecipeStep {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @ManyToOne
    @JoinColumn(name = "recipe_id", nullable = false)
    private Recipe recipe;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String instruction;

    @Column(name = "estimated_time", nullable = true)
    private Integer estimatedTime;

    @Column(name = "timer_minutes")
    private Integer timerMinutes; // 이 단계에 필요한 타이머 시간(분)

    @Column(name = "step_number")
    private Integer stepNumber; // 단계 번호

    @ElementCollection
    @CollectionTable(name = "step_ingredients", joinColumns = @JoinColumn(name = "step_id"))
    @Column(name = "ingredient")
    private List<String> stepIngredients = new ArrayList<>(); // 해당 단계에 필요한 재료들

    @Column(name = "tip", columnDefinition = "TEXT")
    private String tip; // 이 단계에 대한 팁이나 참고사항
}