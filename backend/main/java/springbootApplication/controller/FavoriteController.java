package springbootApplication.controller;

import springbootApplication.domain.Favorite;
import springbootApplication.service.FavoriteService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/favorites")
@Tag(name = "Favorites", description = "Manage user favorite recipes")
public class FavoriteController {

    private final FavoriteService favoriteService;

    public FavoriteController(FavoriteService favoriteService) {
        this.favoriteService = favoriteService;
    }

    @GetMapping
    @Operation(summary = "Get all favorites", description = "Retrieve a list of all user favorites")
    public ResponseEntity<List<Favorite>> getAllFavorites() {
        List<Favorite> favorites = favoriteService.getAllFavorites();
        if (favorites.isEmpty()) {
            return ResponseEntity.noContent().build();  // Return 204 if no favorites found
        }
        return ResponseEntity.ok(favorites);  // Return 200 with the favorites list
    }

    @GetMapping("/{userId}/{recipeId}")
    @Operation(summary = "Get favorite by ID", description = "Retrieve a specific favorite by user ID and recipe ID")
    public ResponseEntity<Favorite> getFavoriteById(
            @PathVariable Long userId, @PathVariable Long recipeId) {
        Optional<Favorite> favorite = favoriteService.getFavoriteByUser_IdAndRecipe_Id(userId, recipeId);
        return favorite.map(ResponseEntity::ok)  // Return 200 with the favorite if found
                .orElseGet(() -> ResponseEntity.notFound().build());  // Return 404 if not found
    }

    @PostMapping
    @Operation(summary = "Add a favorite", description = "Add a recipe to user favorites")
    public ResponseEntity<Favorite> addFavorite(@RequestBody Favorite favorite) {
        try {
            Favorite addedFavorite = favoriteService.addFavorite(favorite);
            return new ResponseEntity<>(addedFavorite, HttpStatus.CREATED);  // Return 201 on success
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).build();  // Return 400 if there's an issue
        }
    }

    @DeleteMapping("/{userId}/{recipeId}")
    @Operation(summary = "Remove a favorite", description = "Remove a specific favorite by user ID and recipe ID")
    public ResponseEntity<Void> removeFavorite(
            @PathVariable Long userId, @PathVariable Long recipeId) {
        try {
            favoriteService.removeFavorite(userId, recipeId);
            return ResponseEntity.noContent().build();  // Return 204 on success
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();  // Return 404 if not found
        }
    }
}
