package springbootApplication.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import springbootApplication.domain.Difficulty;
import springbootApplication.domain.Recipe;
import springbootApplication.dto.ApiResponse;
import springbootApplication.dto.RecipeRequestDto;
import springbootApplication.service.RecipeService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

import java.util.List;

@RestController
@RequestMapping("/api/recipes")
@Tag(name = "Recipes", description = "CRUD & Search operations for recipes")
public class RecipeController {

    private final RecipeService recipeService;

    public RecipeController(RecipeService recipeService) {
        this.recipeService = recipeService;
    }

    @PostMapping("/recommend")
    @Operation(summary = "레시피 추천", description = "사용자 취향에 맞는 레시피 추천")
    public ResponseEntity<ApiResponse<List<Recipe>>> recommendRecipes(@RequestBody RecipeRequestDto dto) {
        List<Recipe> recommendedRecipes = recipeService.getRecommendations(dto);
        return ResponseEntity.ok(ApiResponse.success(recommendedRecipes, "추천 레시피가 성공적으로 조회되었습니다."));
    }

    @GetMapping
    @Operation(summary = "Get all recipes", description = "Retrieve a list of all recipes")
    public ResponseEntity<ApiResponse<List<Recipe>>> getAllRecipes() {
        List<Recipe> recipes = recipeService.getAllRecipes();
        return ResponseEntity.ok(ApiResponse.success(recipes, "모든 레시피가 성공적으로 조회되었습니다."));
    }

    @PostMapping
    @Operation(summary = "Create a new recipe", description = "Add a new recipe")
    public ResponseEntity<ApiResponse<Recipe>> createRecipe(@RequestBody RecipeRequestDto dto) {
        Recipe savedRecipe = recipeService.saveRecipe(dto);
        return ResponseEntity.ok(ApiResponse.success(savedRecipe, "레시피가 성공적으로 저장되었습니다."));
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete a recipe by ID", description = "Delete a recipe by its ID")
    public ResponseEntity<ApiResponse<String>> deleteRecipe(@PathVariable Long id) {
        recipeService.deleteRecipe(id);
        return ResponseEntity.ok(ApiResponse.success("레시피가 성공적으로 삭제되었습니다."));
    }

    @GetMapping("/search")
    @Operation(summary = "Search recipes by keyword", description = "Search for recipes containing the given keyword")
    public ResponseEntity<ApiResponse<List<Recipe>>> searchRecipes(@RequestParam String keyword) {
        List<Recipe> recipes = recipeService.findRecipesByKeyword(keyword);
        return ResponseEntity.ok(ApiResponse.success(recipes, keyword + "에 대한 검색 결과입니다."));
    }

    @GetMapping("/filter")
    @Operation(summary = "Filter recipes", description = "Filter recipes by category and difficulty")
    public ResponseEntity<ApiResponse<List<Recipe>>> filterRecipes(
            @RequestParam String category,
            @RequestParam Difficulty difficulty) {
        List<Recipe> recipes = recipeService.findByDifficulty(difficulty);
        return ResponseEntity.ok(ApiResponse.success(recipes, difficulty + " 난이도의 필터링 결과입니다."));
    }

    @GetMapping("/cooking-time")
    @Operation(summary = "Find recipes by cooking time", description = "Retrieve recipes that match the given cooking time")
    public ResponseEntity<ApiResponse<List<Recipe>>> findRecipesByCookingTime(@RequestParam int cookingTime) {
        List<Recipe> recipes = recipeService.findRecipesByPreparationTime(cookingTime);
        return ResponseEntity.ok(ApiResponse.success(recipes, cookingTime + "분 조리시간에 맞는 레시피입니다."));
    }
}