package springbootApplication.repository;

import springbootApplication.domain.CommunityPost;
import springbootApplication.domain.PostType;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface CommunityPostRepository extends JpaRepository<CommunityPost, Long> {
	Optional<CommunityPost> findByPostIdAndPostType(Long postId, PostType postType);
}
