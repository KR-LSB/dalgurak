package springbootApplication.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import springbootApplication.dto.AIResponseDto;
import springbootApplication.dto.ChatMessageDto;
import springbootApplication.dto.ChatContextDto;
import springbootApplication.dto.EnhancedAIResponseDto;
import springbootApplication.dto.RecipeGuideDto;
import springbootApplication.model.ChatMessage;
import springbootApplication.repository.ChatMessageRepository;
import springbootApplication.repository.UserRepository;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.regex.Pattern;
import java.util.regex.Matcher;

@Service
public class ChatService {
    private static final Logger logger = LoggerFactory.getLogger(ChatService.class);
    private static final int MAX_HISTORY_SIZE = 10;
    private final List<ChatMessage> conversationHistory = new ArrayList<>();

    private final ChatMessageRepository chatMessageRepository;
    private final PythonAIService pythonAIService;
    private final RecipeParserService recipeParserService;
    private final ObjectMapper objectMapper;

    public ChatService(
            ChatMessageRepository chatMessageRepository,
            PythonAIService pythonAIService,
            RecipeParserService recipeParserService,
            ObjectMapper objectMapper
    ) {
        this.chatMessageRepository = chatMessageRepository;
        this.pythonAIService = pythonAIService;
        this.recipeParserService = recipeParserService;
        this.objectMapper = objectMapper;
    }

    public void addToConversationHistory(ChatMessage message) {
        conversationHistory.add(message);

        // 최대 히스토리 크기 유지
        if (conversationHistory.size() > MAX_HISTORY_SIZE) {
            conversationHistory.remove(0);
        }

        // 영구 저장
        chatMessageRepository.save(message);
    }

    public List<ChatMessage> getConversationHistory() {
        return new ArrayList<>(conversationHistory);
    }

    @Transactional
    public EnhancedAIResponseDto processEnhancedAIMessage(ChatMessageDto chatMessageDto) {
        // 사용자 메시지 생성 및 대화 이력 추가
        ChatMessage userMessage = ChatMessage.builder()
                .sender(chatMessageDto.getSender())
                .message(chatMessageDto.getMessage())
                .messageType(ChatMessage.MessageType.USER)
                .build();

        addToConversationHistory(userMessage);

        // 기존 AI 처리 로직 유지
        Instant start = Instant.now();

        try {
            // Python AI 서비스 호출
            String aiResponse = pythonAIService.executeRecipeRAG(chatMessageDto.getMessage());

            Instant end = Instant.now();
            double executionTime = Duration.between(start, end).toMillis() / 1000.0;

            // AI 메시지 생성 및 저장
            ChatMessage aiMessage = ChatMessage.builder()
                    .sender("AI")
                    .message(aiResponse)
                    .messageType(ChatMessage.MessageType.AI)
                    .build();

            addToConversationHistory(aiMessage);

            // 레시피 관련 로직
            boolean isRecipeQuery = isRecipeRelatedQuery(chatMessageDto.getMessage());
            boolean containsRecipeSteps = containsRecipePattern(aiResponse);

            RecipeGuideDto recipeGuide = null;

            if (isRecipeQuery && containsRecipeSteps) {
                try {
                    recipeGuide = recipeParserService.parseStepsFromAIResponse(aiResponse);
                    recipeGuide.setExecutionTime(executionTime);
                    recipeGuide.setOriginalResponse(aiResponse);
                } catch (Exception e) {
                    logger.warn("레시피 파싱 실패: {}", e.getMessage());
                }
            }

            // EnhancedAIResponseDto 생성
            return new EnhancedAIResponseDto(
                    aiResponse,
                    "AI",
                    executionTime,
                    recipeGuide,
                    recipeGuide != null,
                    getConversationHistory()
            );

        } catch (Exception e) {
            // 예외 처리 로직
            logger.error("AI 처리 중 오류 발생", e);

            ChatMessage errorMessage = ChatMessage.builder()
                    .sender("SYSTEM")
                    .message("AI 처리 중 오류 발생: " + e.getMessage())
                    .messageType(ChatMessage.MessageType.SYSTEM)
                    .build();

            addToConversationHistory(errorMessage);

            return new EnhancedAIResponseDto(
                    "오류가 발생했습니다.",
                    "Error",
                    0,
                    null,
                    false,
                    getConversationHistory()
            );
        }
    }

    public AIResponseDto processAIMessage(ChatMessageDto chatMessageDto) {
        EnhancedAIResponseDto enhanced = processEnhancedAIMessage(chatMessageDto);

        return new AIResponseDto(
                enhanced.getAnswer(),
                enhanced.getSource(),
                enhanced.getExecutionTime(),
                enhanced.getConversationContext()
        );
    }

    /**
     * 컨텍스트 정보와 함께 메시지를 처리합니다.
     */
    @Transactional
    public AIResponseDto processMesasgeWithContext(ChatContextDto chatContextDto) {
        // 사용자 메시지 생성 및 대화 이력 추가
        ChatMessage userMessage = ChatMessage.builder()
                .sender(chatContextDto.getSender())
                .message(chatContextDto.getMessage())
                .messageType(ChatMessage.MessageType.USER)
                .build();

        addToConversationHistory(userMessage);

        // 컨텍스트 정보를 포함한 프롬프트 생성
        String contextualPrompt = prepareContextualPrompt(
                chatContextDto.getMessage(),
                chatContextDto.getContext()
        );

        Instant start = Instant.now();

        try {
            // Python AI 서비스 호출 (컨텍스트가 포함된 프롬프트 사용)
            String aiResponse = pythonAIService.executeRecipeRAG(contextualPrompt);

            Instant end = Instant.now();
            double executionTime = Duration.between(start, end).toMillis() / 1000.0;

            // AI 메시지 생성 및 저장
            ChatMessage aiMessage = ChatMessage.builder()
                    .sender("AI")
                    .message(aiResponse)
                    .messageType(ChatMessage.MessageType.AI)
                    .build();

            addToConversationHistory(aiMessage);

            // AIResponseDto 생성
            return new AIResponseDto(
                    aiResponse,
                    "AI",
                    executionTime,
                    getConversationHistory()
            );

        } catch (Exception e) {
            // 예외 처리 로직
            logger.error("컨텍스트 기반 AI 처리 중 오류 발생", e);

            ChatMessage errorMessage = ChatMessage.builder()
                    .sender("SYSTEM")
                    .message("컨텍스트 기반 AI 처리 중 오류 발생: " + e.getMessage())
                    .messageType(ChatMessage.MessageType.SYSTEM)
                    .build();

            addToConversationHistory(errorMessage);

            return new AIResponseDto(
                    "오류가 발생했습니다.",
                    "Error",
                    0,
                    getConversationHistory()
            );
        }
    }

    /**
     * 레시피 관련 질문인지 감지합니다.
     */
    protected boolean isRecipeRelatedQuery(String query) {
        if (query == null) return false;

        String lowerQuery = query.toLowerCase().trim();
        String[] recipeKeywords = {
                "레시피", "요리", "만드는 법", "만들기", "조리법", "요리법",
                "끓이", "볶", "찌개", "반찬", "파스타", "음식"
        };

        for (String keyword : recipeKeywords) {
            if (lowerQuery.contains(keyword)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 응답이 레시피 패턴을 포함하는지 확인합니다.
     */
    protected boolean containsRecipePattern(String response) {
        if (response == null) return false;

        Pattern recipePattern = Pattern.compile(
                "(Step\\s+\\d+:|단계\\s+\\d+:|스텝\\s+\\d+:)",
                Pattern.CASE_INSENSITIVE
        );
        Matcher matcher = recipePattern.matcher(response);

        return matcher.find() &&
                response.contains("재료:") &&
                response.contains("분");
    }

    /**
     * 컨텍스트 정보를 포함한 프롬프트 생성 (개선 버전)
     */
    private String prepareContextualPrompt(String message, ChatContextDto.RecipeContextDto context) {
        StringBuilder promptBuilder = new StringBuilder();

        // 컨텍스트 정보 추가
        promptBuilder.append("현재 요리 중인 레시피: ").append(context.getRecipeTitle()).append("\n");
        promptBuilder.append("현재 단계: ").append(context.getCurrentStep()).append("/").append(context.getTotalSteps()).append("\n");

        if (context.getRecipeType() != null && !context.getRecipeType().isEmpty()) {
            promptBuilder.append("요리 유형: ").append(context.getRecipeType()).append("\n");
        }

        // 사용자의 질문을 마지막에 추가
        promptBuilder.append("\n사용자 질문: ").append(message).append("\n");

        // 명확한 응답 지침 제공
        promptBuilder.append("\n중요 지침: 현재 사용자가 요리 중인 \"").append(context.getRecipeTitle())
                .append("\" 레시피에 대해서만 답변하세요. 다른 레시피를 제공하지 말고, ")
                .append("사용자의 질문에 현재 레시피의 맥락에서 답변해 주세요. ")
                .append("만약 재료 대체나 조리법 변경에 관한 질문이라면, 현재 레시피의 맥락에서 조언을 제공하세요.");

        return promptBuilder.toString();
    }
}