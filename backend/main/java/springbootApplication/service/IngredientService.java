package springbootApplication.service;


import org.springframework.stereotype.Service;
import springbootApplication.domain.Ingredient;
import springbootApplication.repository.IngredientRepository;

import java.util.List;
import java.util.Optional;

@Service
public class IngredientService {

    private final IngredientRepository ingredientRepository;

    public IngredientService(IngredientRepository ingredientRepository) {
        this.ingredientRepository = ingredientRepository;
    }

    public List<Ingredient> getAllIngredients() {
        return ingredientRepository.findAll();
    }

    public Optional<Ingredient> getIngredientById(Long id) {
        return ingredientRepository.findById(id);
    }

    public Ingredient createIngredient(Ingredient ingredient) {
        return ingredientRepository.save(ingredient);
    }

    public Ingredient updateIngredient(Long id, Ingredient updatedIngredient) {
        return ingredientRepository.findById(id)
                .map(ingredient -> {
                    ingredient.setName(updatedIngredient.getName());
                    return ingredientRepository.save(ingredient);
                }).orElseThrow(() -> new RuntimeException("Ingredient not found"));
    }

    public void deleteIngredient(Long id) {
        ingredientRepository.deleteById(id);
    }
}
