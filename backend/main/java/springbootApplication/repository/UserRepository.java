package springbootApplication.repository;
import org.springframework.data.jpa.repository.JpaRepository;
import springbootApplication.domain.User;
import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);
    boolean existsByEmail(String email);
    
    // 사용자명으로 사용자 찾기
    Optional<User> findByUsername(String email);
}