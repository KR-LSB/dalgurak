package springbootApplication.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import springbootApplication.domain.Reply;

import java.util.List;

public interface ReplyRepository extends JpaRepository<Reply, Long> {
    // Changed from findByParentCommentId to match the actual relationship structure
    List<Reply> findByComment_CommentId(Long commentId);
    
    // This method was causing the error - replaced with proper property path
    // List<Reply> findByCommentId(Long commentId);  
    
    List<Reply> findByUser_UserId(Long userId);
}