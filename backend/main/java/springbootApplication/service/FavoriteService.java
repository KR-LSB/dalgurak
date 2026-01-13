package springbootApplication.service;

import springbootApplication.domain.Favorite;
import springbootApplication.repository.FavoriteRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import lombok.RequiredArgsConstructor;

import java.util.List;
import java.util.Optional;

@RequiredArgsConstructor
@Service
public class FavoriteService {

    private final FavoriteRepository favoriteRepository;

    public List<Favorite> getAllFavorites() {
        return favoriteRepository.findAll();
    }

    public Optional<Favorite> getFavoriteByUser_IdAndRecipe_Id(Long userId, Long recipeId) {
        return favoriteRepository.findByUser_UserIdAndRecipe_RecipeId(userId, recipeId);
    }

    @Transactional
    public Favorite addFavorite(Favorite favorite) {
        return favoriteRepository.save(favorite);
    }

    @Transactional
    public void removeFavorite(Long userId, Long recipeId) {
        favoriteRepository.deleteByUser_UserIdAndRecipe_RecipeId(userId, recipeId);
    }
}