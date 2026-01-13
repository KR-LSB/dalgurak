package springbootApplication.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

import springbootApplication.domain.Comment;
import springbootApplication.domain.User;
import springbootApplication.service.CommentService;
import springbootApplication.dto.CommentDto;
import springbootApplication.repository.UserRepository;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

import java.util.List;

@RestController
@RequestMapping("/api/comments")
@Tag(name = "Comments", description = "댓글 관리")
public class CommentController {
   private final CommentService commentService;
   private final UserRepository userRepository;

   public CommentController(CommentService commentService, UserRepository userRepository) {
       this.commentService = commentService;
       this.userRepository = userRepository;
   }

   @GetMapping("/{postId}")
   @Operation(summary = "게시물 댓글 조회", description = "특정 게시물의 모든 댓글 조회")
   public ResponseEntity<List<Comment>> getCommentsByPostId(@PathVariable Long postId) {
       return ResponseEntity.ok(commentService.getCommentsByPostId(postId));
   }
   
   @PostMapping
   @Operation(summary = "댓글 생성", description = "새로운 댓글 작성")
   public ResponseEntity<?> createComment(@RequestBody CommentDto commentDto) {
       try {
           // 현재 인증된 사용자 정보 추출
           Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
           
           if (authentication == null || !authentication.isAuthenticated()) {
               return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                   .body("인증된 사용자가 아닙니다.");
           }
           
           // email 추출
           String email = authentication.getName();
           
           // 사용자 정보 조회
           User currentUser = userRepository.findByEmail(email)
               .orElseThrow(() -> new RuntimeException("사용자를 찾을 수 없습니다."));
           
           // 댓글 DTO에 사용자 ID 설정
           commentDto.setUserId(currentUser.getUserId());
           
           // 로그 출력 (디버깅 목적)
           System.out.println("Authenticated User Email: " + email);
           System.out.println("User ID: " + currentUser.getUserId());
           
           // 댓글 저장
           Comment comment = commentService.addComment(
               commentDto.getPostId(),
               currentUser.getUserId(),
               commentDto.getContent()
           );
           
           return ResponseEntity.ok(comment);
       } catch (Exception e) {
           // 오류 로그 및 메시지 반환
           System.err.println("댓글 생성 중 오류 발생: " + e.getMessage());
           return ResponseEntity.badRequest().body("댓글 생성 실패: " + e.getMessage());
       }
   }
   
   @DeleteMapping("/{commentId}")
   @Operation(summary = "댓글 삭제", description = "특정 댓글 삭제")
   public ResponseEntity<String> deleteComment(@PathVariable Long commentId, @RequestParam Long userId) {
       commentService.deleteComment(commentId, userId);
       return ResponseEntity.ok("Comment deleted successfully");
   }
}