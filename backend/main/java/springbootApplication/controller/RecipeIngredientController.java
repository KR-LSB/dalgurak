package springbootApplication.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import lombok.RequiredArgsConstructor;
import springbootApplication.domain.Recipe;
import springbootApplication.domain.RecipeIngredient;
import springbootApplication.repository.RecipeRepository;
import springbootApplication.service.RecipeIngredientService;

@RestController
@RequestMapping("/api/recipe-ingredients")
@RequiredArgsConstructor
public class RecipeIngredientController {

    private final RecipeIngredientService recipeIngredientService;
    private final RecipeRepository recipeRepository; // RecipeRepository를 주입받습니다

    @PostMapping("/add")
    public ResponseEntity<RecipeIngredient> addRecipeIngredient(@RequestParam Long recipeId,
                                                                @RequestParam String ingredientName,
                                                                @RequestParam String quantity) {
        Recipe recipe = recipeRepository.findById(recipeId)
                .orElseThrow(() -> new RuntimeException("Recipe not found with ID: " + recipeId));

        RecipeIngredient recipeIngredient = recipeIngredientService.createRecipeIngredient(recipe, ingredientName, quantity);
        return ResponseEntity.ok(recipeIngredient);
    }
}
