package springbootApplication.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import springbootApplication.model.ChatMessage;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class AIResponseDto {
    private String answer;
    private String source;
    private double executionTime;
    private List<ChatMessage> conversationContext; // 대화 컨텍스트 추가

    // 기존 생성자 유지
    public AIResponseDto(String answer, String source, double executionTime) {
        this.answer = answer;
        this.source = source;
        this.executionTime = executionTime;
    }

    /**
     * 응답 텍스트를 포맷팅하여 줄바꿈과 구문을 정리합니다.
     *
     * @param rawAnswer 원본 응답 텍스트
     * @return 포맷팅된 응답 텍스트
     */
    public static String formatAnswer(String rawAnswer) {
        if (rawAnswer == null || rawAnswer.trim().isEmpty()) {
            return "";
        }

        // 연속된 줄바꿈 처리
        String formatted = rawAnswer.replaceAll("\\n{3,}", "\n\n");

        // 숫자 목록 형식 정리
        formatted = formatted.replaceAll("(\\d+)\\. ", "\n$1. ");

        return formatted;
    }
}