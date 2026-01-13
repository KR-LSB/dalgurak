package springbootApplication.service;

import org.springframework.stereotype.Service;
import springbootApplication.domain.Ingredient;
import springbootApplication.domain.Recipe;
import springbootApplication.domain.RecipeIngredient;
import springbootApplication.repository.IngredientRepository;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class RecipeIngredientService {

    private final IngredientRepository ingredientRepository;

    public RecipeIngredient createRecipeIngredient(Recipe recipe, String ingredientName, String quantity) {
        // ingredientName을 통해 Ingredient 객체를 찾음
        Ingredient ingredient = ingredientRepository.findByName(ingredientName)
                .orElseThrow(() -> new RuntimeException("Ingredient not found: " + ingredientName));

        // RecipeIngredient 객체 생성
        RecipeIngredient recipeIngredient = new RecipeIngredient(quantity, ingredient, recipe);

        return recipeIngredient;
    }
}