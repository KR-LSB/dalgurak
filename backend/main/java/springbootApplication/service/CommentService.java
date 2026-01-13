package springbootApplication.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;
import springbootApplication.domain.Comment;
import springbootApplication.domain.CommunityPost;
import springbootApplication.repository.CommentRepository;
import springbootApplication.repository.CommunityPostRepository;
import springbootApplication.repository.UserRepository;
import springbootApplication.domain.User;

@Service
@RequiredArgsConstructor
public class CommentService {

    private final CommentRepository commentRepository;
    private final UserRepository userRepository;
    private final CommunityPostRepository communityPostRepository;
    private final WebPushService webPushService;

    // 특정 게시글의 댓글 가져오기
    public List<Comment> getCommentsByPostId(Long postId) {
        return commentRepository.findByPost_PostId(postId);
    }
    
    // 댓글 삭제 (본인만 가능)
    @Transactional
    public void deleteComment(Long commentId, Long userId) {
        Comment comment = commentRepository.findById(commentId)
                .orElseThrow(() -> new RuntimeException("댓글을 찾을 수 없습니다."));

        if (!comment.getUser().getUserId().equals(userId)) {
            throw new RuntimeException("타인이 작성한 댓글은 삭제할 수 없습니다!");
        }

        commentRepository.delete(comment);
    }

    @Transactional
    public Comment addComment(Long postId, Long userId, String content) {
        // 입력값 검증 및 로깅
        System.out.println("Adding comment with postId: " + postId + ", userId: " + userId + ", content: " + content);
        
        if (postId == null) {
            throw new IllegalArgumentException("Post ID cannot be null");
        }
        
        if (userId == null) {
            throw new IllegalArgumentException("User ID cannot be null");
        }
        
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("User not found with ID: " + userId));

        CommunityPost post = communityPostRepository.findById(postId)
                .orElseThrow(() -> new RuntimeException("Post not found with ID: " + postId));

        Comment comment = Comment.builder()
                .post(post)
                .user(user)
                .content(content)
                .build();

        Comment savedComment = commentRepository.save(comment);

        // 댓글 추가 후, 모든 사용자에게 알림 전송
        sendPushNotificationToAllUsers(content);
        
        return savedComment;
    }

    // 댓글 달리면 알림을 모든 사용자에게 보내는 메소드
    private void sendPushNotificationToAllUsers(String message) {
        List<User> allUsers = userRepository.findAll();  // 모든 사용자 조회
        
        for (User user : allUsers) {
            // 각 사용자의 푸시 알림 정보를 얻어야 함
            String endpoint = user.getPushNotificationEndpoint();
            String auth = user.getPushNotificationAuth();
            String p256dh = user.getPushNotificationP256dh();

            // 엔드포인트가 있는 경우에만 알림 전송
            if (endpoint != null && auth != null && p256dh != null) {
                webPushService.sendPushNotification(endpoint, message, auth, p256dh);
            }
        }
    }
}