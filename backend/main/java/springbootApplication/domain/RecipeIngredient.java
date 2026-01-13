package springbootApplication.domain;

import jakarta.persistence.*;
import lombok.*;

import java.io.Serializable;
import java.util.Objects;

@Entity
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "recipe_ingredients")
public class RecipeIngredient {

    @EmbeddedId
    private RecipeIngredientId id;

    @Column(nullable = false)
    private String quantity;

    @ManyToOne
    @MapsId("recipeId")
    @JoinColumn(name = "recipe_id", nullable = false)
    private Recipe recipe;

    @ManyToOne
    @MapsId("ingredientId")
    @JoinColumn(name = "ingredient_id", nullable = false)
    private Ingredient ingredient;
    
    public RecipeIngredient(String quantity, Ingredient ingredient, Recipe recipe) {
        this.quantity = quantity;
        this.ingredient = ingredient;
        this.recipe = recipe;
        this.id = new RecipeIngredientId(recipe.getRecipeId(), ingredient.getIngredientId()); // 복합 키 생성
    }
}

@Embeddable
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
class RecipeIngredientId implements Serializable {
    // serialVersionUID 추가
    private static final long serialVersionUID = 1L;

    @Column(name = "recipe_id")
    private Long recipeId;

    @Column(name = "ingredient_id")
    private Long ingredientId;

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        RecipeIngredientId that = (RecipeIngredientId) o;
        return Objects.equals(recipeId, that.recipeId) && Objects.equals(ingredientId, that.ingredientId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(recipeId, ingredientId);
    }
}
