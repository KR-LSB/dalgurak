package springbootApplication.dto;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class ReplyRequestDto {
    private Long userId;
    private String content;
}
