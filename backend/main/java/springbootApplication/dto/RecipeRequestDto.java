package springbootApplication.dto;

import java.util.List;
import java.util.stream.Collectors;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import springbootApplication.domain.Difficulty;
import springbootApplication.domain.Ingredient;
import springbootApplication.domain.Recipe;
import springbootApplication.domain.RecipeIngredient;
import springbootApplication.repository.IngredientRepository;

@Getter
@Setter
@AllArgsConstructor
@NoArgsConstructor
public class RecipeRequestDto {
    private String title;
    private Difficulty difficulty;
    private List<IngredientDto> ingredients;
    private int preparationTime;
    private String instructions;

    public RecipeRequestDto(String title, Difficulty difficulty, int preparationTime) {
        this.title = title;
        this.difficulty = difficulty;
        this.preparationTime = preparationTime;
    }

    /**
     * DTO를 엔티티로 변환합니다.
     * @param ingredientRepository 재료 조회를 위한 레파지토리
     * @return 생성된 Recipe 엔티티
     */
    public Recipe toEntity(IngredientRepository ingredientRepository) {
        Recipe recipe = new Recipe();
        recipe.setTitle(this.title);
        recipe.setDifficulty(this.difficulty);
        recipe.setPreparationTime(this.preparationTime);
        recipe.setInstructions(this.instructions);

        if (this.ingredients != null && ingredientRepository != null) {
            List<RecipeIngredient> recipeIngredients = this.ingredients.stream()
                .map(dto -> {
                    Ingredient ingredient;
                    
                    // ID로 재료 찾기 시도
                    if (dto.getIngredientId() != null) {
                        ingredient = ingredientRepository.findById(dto.getIngredientId())
                            .orElseThrow(() -> new RuntimeException("Ingredient not found with ID: " + dto.getIngredientId()));
                    } 
                    // 이름으로 재료 찾기 시도
                    else if (dto.getName() != null && !dto.getName().isEmpty()) {
                        ingredient = ingredientRepository.findByName(dto.getName())
                            .orElseThrow(() -> new RuntimeException("Ingredient not found with name: " + dto.getName()));
                    } else {
                        throw new RuntimeException("Either ingredient ID or name must be provided");
                    }

                    return new RecipeIngredient(dto.getQuantity(), ingredient, recipe);
                })
                .collect(Collectors.toList());

            recipe.setIngredients(recipeIngredients);
        }
        
        return recipe;
    }
}