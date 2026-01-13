package springbootApplication.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import springbootApplication.model.ChatMessage;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class EnhancedAIResponseDto {
    private String answer;           // 원본 AI 텍스트 응답
    private String source;           // 응답 소스
    private double executionTime;    // 실행 시간
    private RecipeGuideDto recipeGuide;   // 레시피 정보 (null일 수 있음)
    private boolean recipeDetected;  // 레시피 감지 여부 플래그
    private List<ChatMessage> conversationContext; // 대화 이력 추가

    /**
     * 기존 AIResponseDto로부터 강화된 응답 생성 (레시피 없음)
     */
    public static EnhancedAIResponseDto fromBasicResponse(AIResponseDto basicResponse) {
        return new EnhancedAIResponseDto(
                basicResponse.getAnswer(),
                basicResponse.getSource(),
                basicResponse.getExecutionTime(),
                null,
                false,
                basicResponse.getConversationContext() // 대화 컨텍스트 추가
        );
    }

    /**
     * 레시피 여부에 따라 recipeDetected 필드를 자동으로 설정
     */
    public void setRecipeGuide(RecipeGuideDto recipeGuide) {
        this.recipeGuide = recipeGuide;
        this.recipeDetected = (recipeGuide != null);
    }
}