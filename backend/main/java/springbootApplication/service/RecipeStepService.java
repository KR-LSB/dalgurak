package springbootApplication.service;

import springbootApplication.domain.RecipeStep;
import springbootApplication.repository.RecipeStepRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class RecipeStepService {

    private final RecipeStepRepository recipeStepRepository;

    public RecipeStepService(RecipeStepRepository recipeStepRepository) {
        this.recipeStepRepository = recipeStepRepository;
    }

    public List<RecipeStep> getAllRecipeSteps() {
        return recipeStepRepository.findAll();
    }

    public Optional<RecipeStep> getRecipeStepById(Long id) {
        return recipeStepRepository.findById(id);
    }

    public RecipeStep createRecipeStep(RecipeStep recipeStep) {
        return recipeStepRepository.save(recipeStep);
    }

    public RecipeStep updateRecipeStep(Long id, RecipeStep updatedRecipeStep) {
        return recipeStepRepository.findById(id)
                .map(recipeStep -> {
                    recipeStep.setInstruction(updatedRecipeStep.getInstruction());
                    recipeStep.setEstimatedTime(updatedRecipeStep.getEstimatedTime());
                    return recipeStepRepository.save(recipeStep);
                }).orElseThrow(() -> new RuntimeException("Recipe step not found"));
    }

    public void deleteRecipeStep(Long id) {
        recipeStepRepository.deleteById(id);
    }
}
