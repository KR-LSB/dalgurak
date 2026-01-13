package springbootApplication.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import springbootApplication.domain.Cover;

public interface ImageRepository extends JpaRepository<Cover, Integer> {
}
