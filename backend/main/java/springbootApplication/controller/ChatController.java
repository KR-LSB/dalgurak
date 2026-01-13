package springbootApplication.controller;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import springbootApplication.dto.ChatMessageDto;
import springbootApplication.dto.ChatContextDto;
import springbootApplication.dto.AIResponseDto;
import springbootApplication.dto.EnhancedAIResponseDto;
import springbootApplication.service.ChatService;
import springbootApplication.service.QueryHistoryService;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@RestController
@RequestMapping("/api/chat")
@Tag(name = "Chat", description = "AI 챗봇 메시지 처리")
public class ChatController {
    private static final Logger logger = LoggerFactory.getLogger(ChatController.class);
    private final ChatService chatService;
    private final QueryHistoryService queryHistoryService;


    public ChatController(ChatService chatService, QueryHistoryService queryHistoryService) {
        this.chatService = chatService;
        this.queryHistoryService = queryHistoryService;
    }

    @PostMapping("/ask")
    @Operation(summary = "AI에게 질문하기", description = "사용자 메시지를 저장하고 AI 응답과 함께 레시피 정보를 생성합니다")
    public ResponseEntity<EnhancedAIResponseDto> askAI(@RequestBody ChatMessageDto chatMessageDto) {
        logger.info("AI 질문 수신: {}", chatMessageDto.getMessage());

        // 강화된 응답 (레시피 정보 포함)을 반환하는 메소드 사용
        EnhancedAIResponseDto response = chatService.processEnhancedAIMessage(chatMessageDto);

        // 레시피 관련 질문이고 성공적으로 처리된 경우 히스토리에 저장
        if (response.isRecipeDetected()) {
            logger.info("레시피 응답 생성 완료: {}, 단계수: {}",
                    response.getRecipeGuide().getTitle(),
                    response.getRecipeGuide().getSteps().size());

            // 성공한 쿼리 저장
            queryHistoryService.saveSuccessfulQuery(chatMessageDto.getMessage());
        }

        return ResponseEntity.ok(response);
    }

    @PostMapping("/ask/legacy")
    @Operation(summary = "기존 방식으로 AI에게 질문하기", description = "호환성을 위한 레거시 엔드포인트")
    public ResponseEntity<AIResponseDto> askAILegacy(@RequestBody ChatMessageDto chatMessageDto) {
        logger.info("레거시 AI 질문 수신: {}", chatMessageDto.getMessage());
        AIResponseDto response = chatService.processAIMessage(chatMessageDto);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/ask-with-context")
    @Operation(summary = "컨텍스트와 함께 AI에게 질문하기", description = "요리 가이드 모드에서 컨텍스트(현재 레시피 정보)와 함께 질문합니다")
    public ResponseEntity<AIResponseDto> askAIWithContext(@RequestBody ChatContextDto chatContextDto) {
        logger.info("컨텍스트 포함 AI 질문 수신: {}, 레시피: {}, 단계: {}/{}",
                chatContextDto.getMessage(),
                chatContextDto.getContext().getRecipeTitle(),
                chatContextDto.getContext().getCurrentStep(),
                chatContextDto.getContext().getTotalSteps());

        // 컨텍스트와 함께 메시지 처리 (메서드명 수정)
        AIResponseDto response = chatService.processMesasgeWithContext(chatContextDto);

        return ResponseEntity.ok(response);
    }
}