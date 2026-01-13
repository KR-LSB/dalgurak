package springbootApplication.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;

import springbootApplication.service.QueryHistoryService;
import springbootApplication.service.RecipeParserService;
import springbootApplication.service.ChatService;

import springbootApplication.dto.AIResponseDto;
import springbootApplication.dto.ApiResponse;
import springbootApplication.dto.RecipeGuideDto;
import springbootApplication.dto.RecipeStepDto;
import springbootApplication.dto.ChatMessageDto;

import springbootApplication.model.ChatMessage;

import java.time.Instant;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.Arrays;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/ai")
@Tag(name = "AI Recipe", description = "AI 기반 레시피 서비스")
@RequiredArgsConstructor
public class AIRecipeController {
    private static final Logger logger = LoggerFactory.getLogger(AIRecipeController.class);

    private final RecipeParserService recipeParserService;
    private final ChatService chatService;
    private final QueryHistoryService queryHistoryService;

    // 마지막으로 성공한 쿼리를 저장할 변수
    private static final ThreadLocal<String> lastSuccessfulQuery = new ThreadLocal<>();

    /**
     * AI 레시피 추천 API
     */
    @GetMapping("/recipe")
    @Operation(summary = "AI 레시피 추천", description = "AI가 레시피를 추천합니다")
    public ResponseEntity<ApiResponse<AIResponseDto>> getRecipeRecommendation(@RequestParam String query) {
        logger.info("레시피 추천 요청 받음: {}", query);
        Instant start = Instant.now();

        try {
            // 유효한 쿼리 저장
            if (isValidQuery(query)) {
                lastSuccessfulQuery.set(query);
                logger.info("유효한 쿼리 저장됨: {}", query);
            }

            ChatMessageDto chatMessageDto = new ChatMessageDto();
            chatMessageDto.setSender("User");
            chatMessageDto.setMessage(query);

            AIResponseDto responseDto = chatService.processAIMessage(chatMessageDto);

            logger.info("레시피 추천 응답 생성 완료: {}초", responseDto.getExecutionTime());
            return ResponseEntity.ok(ApiResponse.success(responseDto, "AI 레시피 추천이 성공적으로 완료되었습니다."));

        } catch (Exception e) {
            logger.error("레시피 추천 중 오류 발생", e);
            return ResponseEntity
                    .status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.error(HttpStatus.INTERNAL_SERVER_ERROR, "AI 추천 중 오류가 발생했습니다: " + e.getMessage()));
        }
    }

    /**
     * 단계별 레시피 가이드 API
     */
    @GetMapping("/recipe-steps")
    @Operation(summary = "단계별 레시피 가이드", description = "AI가 단계별 레시피 가이드를 제공합니다")
    public ResponseEntity<ApiResponse<RecipeGuideDto>> getRecipeGuide(@RequestParam String query) {
        String requestId = UUID.randomUUID().toString();
        logger.info("[{}] 레시피 가이드 요청 받음. 원본 쿼리: [{}]", requestId, query);
        Instant start = Instant.now();

        try {
            // 쿼리 검증 및 교정
            String effectiveQuery = validateAndCorrectQuery(query, requestId);

            logger.info("[{}] 유효한 쿼리로 처리 중: [{}]", requestId, effectiveQuery);

            // ChatService를 통해 AI 응답 가져오기
            ChatMessageDto chatMessageDto = new ChatMessageDto();
            chatMessageDto.setSender("User");
            chatMessageDto.setMessage(effectiveQuery);

            AIResponseDto aiResponse = chatService.processAIMessage(chatMessageDto);

            logger.info("[{}] AI 응답 길이: {}, 앞부분: [{}...]",
                    requestId,
                    aiResponse.getAnswer().length(),
                    aiResponse.getAnswer().substring(0, Math.min(100, aiResponse.getAnswer().length())));

            // AI 응답을 구조화된 단계별 가이드로 변환
            RecipeGuideDto recipeGuide = recipeParserService.parseStepsFromAIResponse(aiResponse.getAnswer());

            // 실행 시간 및 원본 응답 설정
            recipeGuide.setExecutionTime(aiResponse.getExecutionTime());
            recipeGuide.setOriginalResponse(aiResponse.getAnswer());

            // 대화 컨텍스트 기반 추가 로직
            List<ChatMessage> recentContext = aiResponse.getConversationContext();

            Optional<ChatMessage> dietaryRestriction = recentContext.stream()
                    .filter(msg ->
                            msg.getMessage().contains("채식") ||
                                    msg.getMessage().contains("알레르기") ||
                                    msg.getMessage().contains("글루텐") ||
                                    msg.getMessage().contains("유제품")
                    )
                    .findFirst();

            dietaryRestriction.ifPresent(restriction -> {
                if (recipeGuide != null) {
                    recipeGuide.getSteps().add(
                            RecipeStepDto.builder()
                                    .stepNumber(recipeGuide.getSteps().size() + 1)
                                    .instruction("⚠️ 특별한 식단 요구사항 참고: " + restriction.getMessage())
                                    .build()
                    );
                }
            });

            logger.info("[{}] 레시피 가이드 생성 완료. 제목: {}, 단계 수: {}, 소요시간: {}초",
                    requestId,
                    recipeGuide.getTitle(),
                    recipeGuide.getSteps().size(),
                    recipeGuide.getExecutionTime());

            return ResponseEntity.ok(ApiResponse.success(recipeGuide, "레시피 가이드가 성공적으로 생성되었습니다."));

        } catch (Exception e) {
            logger.error("[{}] 레시피 가이드 생성 중 오류 발생: {}", requestId, e.getMessage(), e);
            return ResponseEntity
                    .status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.error(HttpStatus.INTERNAL_SERVER_ERROR, "가이드 생성 중 오류가 발생했습니다: " + e.getMessage()));
        } finally {
            // 처리 완료 후 ThreadLocal 정리
            lastSuccessfulQuery.remove();
        }
    }

    /**
     * 재료 대체 추천 API
     */
    @GetMapping("/ingredient-substitute")
    @Operation(summary = "재료 대체 추천", description = "AI가 재료 대체를 추천합니다")
    public ResponseEntity<ApiResponse<AIResponseDto>> getIngredientSubstitute(@RequestParam String ingredient) {
        logger.info("재료 대체 추천 요청 받음: {}", ingredient);
        Instant start = Instant.now();

        try {
            String query = ingredient + " 대신 사용할 수 있는 재료는?";

            ChatMessageDto chatMessageDto = new ChatMessageDto();
            chatMessageDto.setSender("User");
            chatMessageDto.setMessage(query);

            AIResponseDto responseDto = chatService.processAIMessage(chatMessageDto);

            logger.info("재료 대체 추천 응답 생성 완료: {}초", responseDto.getExecutionTime());
            return ResponseEntity.ok(ApiResponse.success(responseDto, "재료 대체 추천이 성공적으로 완료되었습니다."));

        } catch (Exception e) {
            logger.error("재료 대체 추천 중 오류 발생", e);
            return ResponseEntity
                    .status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.error(HttpStatus.INTERNAL_SERVER_ERROR, "재료 대체 추천 중 오류가 발생했습니다: " + e.getMessage()));
        }
    }

    /**
     * 쿼리 유효성 검사
     */
    private boolean isValidQuery(String query) {
        if (query == null || query.trim().isEmpty()) {
            return false;
        }

        String trimmed = query.trim();
        return trimmed.length() >= 2 &&
                !trimmed.contains("[") &&
                !trimmed.contains("]");
    }

    /**
     * 쿼리 검증 및 교정
     */
    private String validateAndCorrectQuery(String query, String requestId) {
        // 1. 기본적인 유효성 검사
        if (!isValidQuery(query)) {
            String lastQuery = queryHistoryService.getLastSuccessfulQuery();
            logger.warn("[{}] 잘못된 쿼리 [{}] 대신 마지막 유효 쿼리 [{}] 사용", requestId, query, lastQuery);
            return lastQuery;
        }

        // 2. 일반적인 쿼리 검사 추가
        Set<String> generalQueries = new HashSet<>(Arrays.asList(
                "레시피", "요리", "음식", "요리법", "메뉴", "추천", "인기", "맛있는", "만들기", "조리법"
        ));

        String trimmedQuery = query.trim().toLowerCase();
        if (generalQueries.contains(trimmedQuery)) {
            // 일반적인 쿼리인 경우 마지막 성공 쿼리 사용
            String lastQuery = queryHistoryService.getLastSuccessfulQuery();
            logger.info("[{}] 일반적인 쿼리 [{}] 대신 마지막 성공 쿼리 [{}] 사용", requestId, query, lastQuery);
            return lastQuery;
        }

        // 3. 구체적인 쿼리는 그대로 사용
        return query.trim();
    }
}