package springbootApplication.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import springbootApplication.domain.Difficulty;
import springbootApplication.domain.Ingredient;
import springbootApplication.domain.Recipe;
import springbootApplication.domain.RecipeIngredient;
import springbootApplication.dto.IngredientDto;
import springbootApplication.dto.RecipeRequestDto;
import springbootApplication.repository.IngredientRepository;
import springbootApplication.repository.RecipeRepository;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class RecipeService {

    private final RecipeRepository recipeRepository;
    private final IngredientRepository ingredientRepository;

    /**
     * 모든 레시피를 조회합니다.
     * @return 레시피 목록
     */
    public List<Recipe> getAllRecipes() {
        return recipeRepository.findAll();
    }

    /**
     * ID로 레시피를 조회합니다.
     * @param id 레시피 ID
     * @return 레시피(Optional)
     */
    public Optional<Recipe> getRecipeById(Long id) {
        return recipeRepository.findById(id);
    }

    /**
     * 새로운 레시피를 저장합니다.
     * @param dto 레시피 요청 DTO
     * @return 저장된 레시피
     */
    @Transactional
    public Recipe saveRecipe(RecipeRequestDto dto) {
        if (dto.getDifficulty() == null) {
            throw new RuntimeException("Difficulty value cannot be null");
        }

        try {
            Recipe recipe = dto.toEntity(ingredientRepository);
            return recipeRepository.save(recipe);
        } catch (IllegalArgumentException e) {
            throw new RuntimeException("Invalid recipe data: " + e.getMessage());
        }
    }

    /**
     * 레시피를 업데이트합니다.
     * @param id 레시피 ID
     * @param updatedRecipe 업데이트할 레시피 정보
     * @return 업데이트된 레시피
     */
    @Transactional
    public Recipe updateRecipe(Long id, Recipe updatedRecipe) {
        return recipeRepository.findById(id)
                .map(existingRecipe -> {
                    existingRecipe.setTitle(updatedRecipe.getTitle());
                    existingRecipe.setInstructions(updatedRecipe.getInstructions());
                    existingRecipe.setPreparationTime(updatedRecipe.getPreparationTime());
                    existingRecipe.setDifficulty(updatedRecipe.getDifficulty());
                    return recipeRepository.save(existingRecipe);
                })
                .orElseThrow(() -> new RuntimeException("Recipe not found"));
    }

    /**
     * 레시피를 삭제합니다.
     * @param id 레시피 ID
     */
    @Transactional
    public void deleteRecipe(Long id) {
        if (!recipeRepository.existsById(id)) {
            throw new RuntimeException("Recipe not found");
        }
        recipeRepository.deleteById(id);
    }

    /**
     * 키워드로 레시피를 검색합니다.
     * @param keyword 검색 키워드
     * @return 검색된 레시피 목록
     */
    public List<Recipe> findRecipesByKeyword(String keyword) {
        return recipeRepository.findByTitleContaining(keyword);
    }

    /**
     * 난이도로 레시피를 필터링합니다.
     * @param difficulty 난이도
     * @return 필터링된 레시피 목록
     */
    public List<Recipe> findByDifficulty(Difficulty difficulty) {
        return recipeRepository.findByDifficulty(difficulty);
    }

    /**
     * 조리 시간으로 레시피를 검색합니다.
     * @param preparationTime 조리 시간
     * @return 검색된 레시피 목록
     */
    public List<Recipe> findRecipesByPreparationTime(int preparationTime) {
        return recipeRepository.findByPreparationTime(preparationTime);
    }

    /**
     * 사용자의 선호도에 맞는 레시피를 추천합니다.
     * 난이도, 준비 시간, 재료를 고려하여 추천합니다.
     * @param dto 레시피 요청 DTO
     * @return 추천된 레시피 목록
     */
    public List<Recipe> getRecommendations(RecipeRequestDto dto) {
        // 기본 필터링 조건 설정
        Difficulty requestedDifficulty = dto.getDifficulty();
        int requestedPrepTime = dto.getPreparationTime();
        
        // 1. 기본 레시피 목록 가져오기
        List<Recipe> candidates = recipeRepository.findAll();
        
        // 2. 난이도 기반 필터링 (난이도가 지정된 경우)
        if (requestedDifficulty != null) {
            candidates = candidates.stream()
                .filter(recipe -> recipe.getDifficulty() == requestedDifficulty)
                .collect(Collectors.toList());
        }
        
        // 3. 시간 제약 고려 (요청된 준비 시간이 0보다 큰 경우)
        if (requestedPrepTime > 0) {
            int timeLowerBound = (int)(requestedPrepTime * 0.8);
            int timeUpperBound = (int)(requestedPrepTime * 1.2);
            
            candidates = candidates.stream()
                .filter(recipe -> recipe.getPreparationTime() >= timeLowerBound && 
                                 recipe.getPreparationTime() <= timeUpperBound)
                .collect(Collectors.toList());
        }
        
        // 4. 재료 유사성 기반 추천
        if (dto.getIngredients() != null && !dto.getIngredients().isEmpty()) {
            // 선호하는 재료 ID 목록 추출
            List<Long> preferredIngredientIds = dto.getIngredients().stream()
                .map(IngredientDto::getIngredientId)
                .filter(Objects::nonNull)  // null이 아닌 ID만 필터링
                .collect(Collectors.toList());
            
            // 선호하는 재료 이름 목록 추출
            List<String> preferredIngredientNames = dto.getIngredients().stream()
                .map(IngredientDto::getName)
                .filter(name -> name != null && !name.isEmpty())  // 유효한 이름만 필터링
                .collect(Collectors.toList());
            
            // 유사도 점수를 계산하여 정렬
            Map<Recipe, Integer> recipeScores = new HashMap<>();
            
            for (Recipe recipe : candidates) {
                int score = 0;
                
                // 레시피의 재료 정보 추출
                if (recipe.getIngredients() != null) {
                    for (RecipeIngredient ri : recipe.getIngredients()) {
                        Ingredient ingredient = ri.getIngredient();
                        
                        // ID 또는 이름으로 일치 여부 확인
                        if (preferredIngredientIds.contains(ingredient.getIngredientId()) || 
                            preferredIngredientNames.contains(ingredient.getName())) {
                            score++;
                        }
                    }
                }
                
                recipeScores.put(recipe, score);
            }
            
            // 점수에 따라 정렬 (점수가 높은 순)
            candidates = recipeScores.entrySet().stream()
                .sorted(Map.Entry.<Recipe, Integer>comparingByValue().reversed())
                .map(Map.Entry::getKey)
                .collect(Collectors.toList());
        }
        
        // 최대 5개의 추천 레시피 반환
        return candidates.stream().limit(5).collect(Collectors.toList());
    }
}