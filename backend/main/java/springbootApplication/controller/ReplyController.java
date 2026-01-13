package springbootApplication.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import springbootApplication.domain.Reply;
import springbootApplication.dto.ReplyRequestDto;
import springbootApplication.service.ReplyService;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

import java.util.List;

@RestController
@RequestMapping("/api/replies")
@Tag(name = "Replies", description = "댓글 답글 관리")
public class ReplyController {

    private final ReplyService replyService;

    public ReplyController(ReplyService replyService) {
        this.replyService = replyService;
    }

    @GetMapping("/{commentId}")
    @Operation(summary = "댓글 답글 조회", description = "특정 댓글의 모든 답글 조회")
    public ResponseEntity<List<Reply>> getRepliesByCommentId(@PathVariable Long commentId) {
        return ResponseEntity.ok(replyService.getRepliesByCommentId(commentId));
    }

    @DeleteMapping("/{replyId}")
    @Operation(summary = "답글 삭제", description = "특정 답글 삭제")
    public ResponseEntity<String> deleteReply(@PathVariable Long replyId, @RequestParam Long userId) {
        replyService.deleteReply(replyId, userId);
        return ResponseEntity.ok("Reply deleted successfully");
    }

    @PostMapping("/{commentId}")
    @Operation(summary = "답글 생성", description = "특정 댓글에 대한 새로운 답글 작성")
    public ResponseEntity<Reply> createReply(@PathVariable Long commentId,
                                             @RequestBody ReplyRequestDto requestDto) {
        Reply reply = replyService.addReply(commentId, requestDto.getUserId(), requestDto.getContent());
        return ResponseEntity.ok(reply);
    }
}