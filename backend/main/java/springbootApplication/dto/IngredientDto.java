package springbootApplication.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class IngredientDto {
    private Long ingredientId;  // 변수명 수정
    private String name;
    private String quantity;  // 변수명 수정
}
