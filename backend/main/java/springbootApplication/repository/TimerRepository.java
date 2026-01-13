package springbootApplication.repository;

import springbootApplication.domain.Timer; // 올바른 경로로 수정
import org.springframework.data.jpa.repository.JpaRepository;

public interface TimerRepository extends JpaRepository<Timer, Long> {
}
