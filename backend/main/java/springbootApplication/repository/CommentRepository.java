package springbootApplication.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import springbootApplication.domain.Comment;

import java.util.List;
import java.util.Optional;

public interface CommentRepository extends JpaRepository<Comment, Long> {
    // 특정 게시글의 ID로 댓글 목록을 조회하는 메서드
    List<Comment> findByPost_PostId(Long postId);

    Optional<Comment> findById(Long id);
}