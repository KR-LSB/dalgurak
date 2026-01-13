package springbootApplication.repository;

import springbootApplication.domain.Recipe;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import springbootApplication.domain.Difficulty;

public interface RecipeRepository extends JpaRepository<Recipe, Long> {

	List<Recipe> findByTitleContaining(String keyword);

	    // ✅ 난이도로 레시피 검색
	 List<Recipe> findByDifficulty(Difficulty difficulty);

	    // ✅ 준비 시간(분 단위)으로 레시피 검색
	    List<Recipe> findByPreparationTime(int preparationTime);
}


