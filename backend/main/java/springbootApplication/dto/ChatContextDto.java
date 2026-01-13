package springbootApplication.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class ChatContextDto {
    private String sender;
    private String message;
    private RecipeContextDto context;

    @Getter
    @Setter
    public static class RecipeContextDto {
        private String recipeTitle;
        private int currentStep;
        private int totalSteps;
        private String recipeType;
    }
}