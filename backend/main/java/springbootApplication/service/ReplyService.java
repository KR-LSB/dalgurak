package springbootApplication.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import lombok.RequiredArgsConstructor;
import springbootApplication.domain.Reply;
import springbootApplication.domain.Comment;
import springbootApplication.domain.User;
import springbootApplication.repository.ReplyRepository;
import springbootApplication.repository.UserRepository;
import springbootApplication.repository.CommentRepository;

import java.util.List;

@RequiredArgsConstructor
@Service
public class ReplyService {
    
    private final ReplyRepository replyRepository;
    private final UserRepository userRepository;
    private final CommentRepository commentRepository;
    private final WebPushService webPushService;

    // 특정 댓글의 답글 가져오기 - 메서드 수정
    public List<Reply> getRepliesByCommentId(Long commentId) {
        // Changed from findByCommentId to findByComment_CommentId
        return replyRepository.findByComment_CommentId(commentId);
    }

    // 답글 삭제 (본인만 가능)
    @Transactional
    public void deleteReply(Long replyId, Long userId) {
        Reply reply = replyRepository.findById(replyId)
                .orElseThrow(() -> new RuntimeException("Reply not found"));

        if (!reply.getUser().getUserId().equals(userId)) {
            throw new RuntimeException("You can only delete your own reply!");
        }

        replyRepository.delete(reply);
    }

    // 답글 추가
    @Transactional
    public Reply addReply(Long commentId, Long userId, String content) {
        Comment comment = commentRepository.findById(commentId)
                .orElseThrow(() -> new RuntimeException("Comment not found"));
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("User not found"));

        Reply reply = Reply.builder()
                .comment(comment)
                .user(user)
                .content(content)
                .build();

        Reply savedReply = replyRepository.save(reply);

        Long commentAuthorId = comment.getUser().getUserId();
        sendReplyNotificationToCommentAuthor(commentAuthorId, savedReply);

        return savedReply;
    }

    // 댓글 작성자에게 답글 알림 보내기
    private void sendReplyNotificationToCommentAuthor(Long commentAuthorId, Reply reply) {
        User user = userRepository.findById(commentAuthorId)
                .orElseThrow(() -> new RuntimeException("User not found"));

        String message = "Someone replied to your comment: " + reply.getContent();

        webPushService.sendPushNotification(
                user.getPushNotificationEndpoint(),
                message,
                user.getPushNotificationAuth(),
                user.getPushNotificationP256dh()
        );
    }
}