package springbootApplication.dto;

import java.util.List;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 단계별 레시피 가이드 정보를 담는 DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RecipeGuideDto {
    /** 레시피 제목 */
    private String title;

    /** 단계별 지시사항 목록 */
    private List<RecipeStepDto> steps;

    /** 재료 목록 */
    private List<String> ingredients;

    /** 총 조리 시간(분) */
    private int totalTimeMinutes;

    /** API 실행 시간(초) */
    private double executionTime;

    /** 원본 AI 응답 */
    private String originalResponse;

    /** 일관성 경고 메시지 */
    private String consistencyWarning;
}