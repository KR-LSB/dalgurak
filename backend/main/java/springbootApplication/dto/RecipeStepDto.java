package springbootApplication.dto;

import java.util.List;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 레시피의 각 단계 정보를 담는 DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RecipeStepDto {
    /** 단계 번호 */
    private int stepNumber;

    /** 단계별 조리 지침 */
    private String instruction;

    /** 타이머 시간(분) */
    private int timerMinutes;

    /** 해당 단계에 필요한 재료들 */
    private List<String> stepIngredients;

    /** 부가적인 팁 정보 */
    private String tip;
}