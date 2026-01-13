package springbootApplication.repository;

import springbootApplication.domain.Favorite;
import springbootApplication.domain.FavoriteId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface FavoriteRepository extends JpaRepository<Favorite, FavoriteId> {

    // 수정된 메서드 - User 엔티티의 userId 필드와 Recipe 엔티티의 recipeId 필드를 참조
    Optional<Favorite> findByUser_UserIdAndRecipe_RecipeId(Long userId, Long recipeId);

    // 수정된 메서드 - User 엔티티의 userId 필드와 Recipe 엔티티의 recipeId 필드를 참조
    void deleteByUser_UserIdAndRecipe_RecipeId(Long userId, Long recipeId);
}