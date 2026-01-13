package springbootApplication.dto;

import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class CommentDto {
    private Long postId;
    private String userIdStr;  // 문자열 형태의 userId
    private Long userId;        // 숫자 형태의 userId
    private String content;

    // 추가: userIdStr이 제공될 경우 userId로 변환하는 메서드
    public void processUserId() {
        if (userId == null && userIdStr != null) {
            try {
                // 숫자로 시작하는 문자열이면 Long으로 변환
                if (userIdStr.matches("\\d+")) {
                    userId = Long.parseLong(userIdStr);
                }
            } catch (NumberFormatException e) {
                // 변환 실패 시 처리
                userId = null;
            }
        }
    }
}
