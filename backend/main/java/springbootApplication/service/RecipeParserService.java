package springbootApplication.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import springbootApplication.dto.RecipeGuideDto;
import springbootApplication.dto.RecipeStepDto;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * AI 응답을 구조화된 레시피 가이드로 변환하는 서비스
 */
@Service
public class RecipeParserService {
    private static final Logger logger = LoggerFactory.getLogger(RecipeParserService.class);

    // 기본 정규식 패턴들
    private static final Pattern STEP_PATTERN = Pattern.compile("Step (\\d+)[:\\.]\\s*(.+?)(?=(Step \\d+|$))", Pattern.DOTALL);
    private static final Pattern TIME_PATTERN = Pattern.compile("(\\d+)\\s*분", Pattern.DOTALL);
    private static final Pattern INGREDIENT_PATTERN = Pattern.compile("재료:[\\s\\n]+(.*?)(?=Step|단계|스텝|$)", Pattern.DOTALL);
    private static final Pattern TITLE_PATTERN = Pattern.compile("레시피:\\s*([^\\n]+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern TOTAL_TIME_PATTERN = Pattern.compile("총\\s*(?:조리)?\\s*시간:?\\s*(\\d+)\\s*분", Pattern.CASE_INSENSITIVE);
    private static final Pattern INGREDIENT_ITEM_PATTERN = Pattern.compile("[-•●]\\s*([^\\n]+)", Pattern.MULTILINE);

    // 한글 레시피 관련 패턴들
    private static final Pattern KOREAN_STEP_PATTERN = Pattern.compile("(단계|스텝|Step)\\s*(\\d+)[:\\.]\\s*(.+?)(?=(단계|스텝|Step)\\s*\\d+|$)", Pattern.DOTALL | Pattern.CASE_INSENSITIVE);
    private static final Pattern KOREAN_TIME_PATTERN = Pattern.compile("(\\d+)\\s*분(?:간|\\s+소요|\\s+정도)?", Pattern.CASE_INSENSITIVE);

    /**
     * AI 응답을 구조화된 레시피 가이드로 변환합니다.
     *
     * @param aiResponse AI 응답 텍스트
     * @return 레시피 가이드 DTO
     */
    public RecipeGuideDto parseStepsFromAIResponse(String aiResponse) {
        logger.debug("원본 AI 응답: {}", aiResponse);

        if (aiResponse == null || aiResponse.trim().isEmpty()) {
            throw new IllegalArgumentException("AI 응답이 비어있습니다.");
        }

        RecipeGuideDto guide = new RecipeGuideDto();

        // 제목 추출
        String title = extractTitle(aiResponse);
        logger.debug("추출된 제목: {}", title);
        guide.setTitle(title);

        // 재료 목록 추출
        List<String> ingredients = extractIngredients(aiResponse);
        logger.debug("추출된 재료 목록: {}", ingredients);
        guide.setIngredients(ingredients);

        // 단계별 지시사항 추출
        List<RecipeStepDto> steps = extractSteps(aiResponse);
        if (!steps.isEmpty()) {
            logger.debug("추출된 단계 수: {}, 첫 번째 단계: {}", steps.size(), steps.get(0).getInstruction());
        } else {
            logger.warn("추출된 단계가 없습니다.");
        }
        guide.setSteps(steps);

        // 총 소요 시간 추출 또는 계산
        int totalTime = extractTotalTime(aiResponse);
        if (totalTime <= 0) {
            totalTime = calculateTotalTime(steps);
        }
        guide.setTotalTimeMinutes(totalTime);

        // 원본 응답도 저장 (디버깅용)
        guide.setOriginalResponse(aiResponse);

        return guide;
    }

    /**
     * AI 응답에서 레시피 제목을 추출합니다.
     */
    private String extractTitle(String aiResponse) {
        // 한글 레시피 제목 패턴 ("레시피: 김치찌개" 형식)
        Matcher koreanTitleMatcher = TITLE_PATTERN.matcher(aiResponse);
        if (koreanTitleMatcher.find()) {
            return koreanTitleMatcher.group(1).trim();
        }

        // 첫 줄이 제목일 가능성 검사
        String[] lines = aiResponse.split("\n");
        for (String line : lines) {
            line = line.trim();
            if (!line.isEmpty() && !line.startsWith("Step") && !line.startsWith("단계")
                    && !line.startsWith("스텝") && !line.contains("재료:")) {
                return line;
            }
        }

        return "레시피 가이드";
    }

    /**
     * AI 응답에서 재료 목록을 추출합니다.
     */
    private List<String> extractIngredients(String aiResponse) {
        List<String> ingredients = new ArrayList<>();

        Matcher ingredientsMatcher = INGREDIENT_PATTERN.matcher(aiResponse);
        if (ingredientsMatcher.find()) {
            String ingredientsText = ingredientsMatcher.group(1).trim();

            // 재료가 목록 형식으로 나열된 경우 (-로 시작하는 항목)
            Matcher itemMatcher = INGREDIENT_ITEM_PATTERN.matcher(ingredientsText);
            while (itemMatcher.find()) {
                ingredients.add(itemMatcher.group(1).trim());
            }

            // 목록 형식이 아닌 경우 줄 단위로 추출
            if (ingredients.isEmpty()) {
                String[] lines = ingredientsText.split("\n");
                for (String line : lines) {
                    line = line.trim();
                    if (!line.isEmpty()) {
                        ingredients.add(line);
                    }
                }
            }
        }

        return ingredients;
    }

    /**
     * AI 응답에서 요리 단계를 추출합니다.
     */
    private List<RecipeStepDto> extractSteps(String aiResponse) {
        List<RecipeStepDto> steps = new ArrayList<>();

        // 한글/영문 혼합 단계 패턴 시도
        Matcher koreanStepMatcher = KOREAN_STEP_PATTERN.matcher(aiResponse);
        while (koreanStepMatcher.find()) {
            int stepNumber = Integer.parseInt(koreanStepMatcher.group(2));
            String instruction = koreanStepMatcher.group(3).trim();

            RecipeStepDto step = new RecipeStepDto();
            step.setStepNumber(stepNumber);
            step.setInstruction(instruction);

            // 시간 정보 추출
            int timerMinutes = extractCookingTime(instruction);
            step.setTimerMinutes(timerMinutes);

            // 해당 단계에 필요한 재료 추출 (필요시)
            step.setStepIngredients(new ArrayList<>()); // 빈 리스트 초기화

            steps.add(step);
        }

        // 한글/영문 혼합 패턴으로 추출 실패 시 기본 영문 패턴 시도
        if (steps.isEmpty()) {
            Matcher stepMatcher = STEP_PATTERN.matcher(aiResponse);
            while (stepMatcher.find()) {
                int stepNumber = Integer.parseInt(stepMatcher.group(1));
                String instruction = stepMatcher.group(2).trim();

                RecipeStepDto step = new RecipeStepDto();
                step.setStepNumber(stepNumber);
                step.setInstruction(instruction);

                // 시간 정보 추출
                int timerMinutes = extractCookingTime(instruction);
                step.setTimerMinutes(timerMinutes);

                // 해당 단계에 필요한 재료 추출 (필요시)
                step.setStepIngredients(new ArrayList<>()); // 빈 리스트 초기화

                steps.add(step);
            }
        }

        // 단계별 패턴 추출 실패 시 텍스트 단락으로 시도
        if (steps.isEmpty()) {
            steps = extractStepsByParagraphs(aiResponse);
        }

        // 단계 번호로 정렬
        steps.sort(Comparator.comparingInt(RecipeStepDto::getStepNumber));

        return steps;
    }

    /**
     * 단락을 기반으로 요리 단계를 추출합니다 (대체 방법).
     */
    private List<RecipeStepDto> extractStepsByParagraphs(String aiResponse) {
        logger.debug("단계 패턴 추출 실패, 단락으로 추출 시도");

        List<RecipeStepDto> steps = new ArrayList<>();
        String[] paragraphs = aiResponse.split("\n\n");
        int stepNumber = 1;

        // 재료 섹션을 건너뛰기 위한 플래그
        boolean ingredientSectionPassed = false;

        for (String paragraph : paragraphs) {
            paragraph = paragraph.trim();
            // 빈 단락 스킵
            if (paragraph.isEmpty()) {
                continue;
            }

            // 재료 섹션인지 확인
            if (!ingredientSectionPassed && (paragraph.startsWith("재료:") || paragraph.contains("재료 목록"))) {
                ingredientSectionPassed = true;
                continue;
            }

            // 제목이나 총 소요시간 등 스킵
            if (paragraph.startsWith("레시피:") || paragraph.contains("총 조리시간")) {
                continue;
            }

            // 이미 단계별 형식이면 스킵 (1. xxx, 2. xxx 형식)
            if (paragraph.matches("^\\d+\\..*")) {
                continue;
            }

            // 실제 요리 지시사항인지 확인 (의미 있는 내용)
            if (ingredientSectionPassed && paragraph.length() > 10) {
                RecipeStepDto step = new RecipeStepDto();
                step.setStepNumber(stepNumber++);
                step.setInstruction(paragraph);

                // 시간 정보 추출
                int timerMinutes = extractCookingTime(paragraph);
                step.setTimerMinutes(timerMinutes);

                // 빈 재료 리스트 초기화
                step.setStepIngredients(new ArrayList<>());

                steps.add(step);
            }
        }

        return steps;
    }

    /**
     * 지시 사항에서 조리 시간을 추출합니다.
     */
    private int extractCookingTime(String text) {
        // 한글 시간 패턴 (예: 약 5분 소요, 5분간 끓이기)
        Matcher koreanTimeMatcher = KOREAN_TIME_PATTERN.matcher(text);
        if (koreanTimeMatcher.find()) {
            try {
                return Integer.parseInt(koreanTimeMatcher.group(1));
            } catch (NumberFormatException e) {
                return 0;
            }
        }

        // 영문 패턴도 확인 (기존 패턴)
        Matcher timeMatcher = TIME_PATTERN.matcher(text);
        if (timeMatcher.find()) {
            try {
                return Integer.parseInt(timeMatcher.group(1));
            } catch (NumberFormatException e) {
                return 0;
            }
        }

        return 0;
    }

    /**
     * AI 응답에서 총 소요 시간을 추출합니다.
     */
    private int extractTotalTime(String aiResponse) {
        Matcher totalTimeMatcher = TOTAL_TIME_PATTERN.matcher(aiResponse);
        if (totalTimeMatcher.find()) {
            try {
                return Integer.parseInt(totalTimeMatcher.group(1));
            } catch (NumberFormatException e) {
                logger.warn("총 조리시간 변환 실패: {}", e.getMessage());
                return 0;
            }
        }
        return 0;
    }

    /**
     * 각 단계의 시간을 합산하여 총 소요 시간을 계산합니다.
     */
    private int calculateTotalTime(List<RecipeStepDto> steps) {
        return steps.stream()
                .mapToInt(RecipeStepDto::getTimerMinutes)
                .sum();
    }

    /**
     * 질문과 생성된 레시피 가이드의 일관성을 검사합니다.
     *
     * @param query 사용자 질문
     * @param guide 생성된 레시피 가이드
     * @return 일관성 경고 메시지 (없으면 null)
     */
    public String validateRecipeConsistency(String query, RecipeGuideDto guide) {
        // 주요 레시피 키워드 추출 (쿼리에서)
        List<String> queryKeywords = extractFoodKeywords(query);

        // 가이드 제목에서 키워드 추출
        List<String> titleKeywords = extractFoodKeywords(guide.getTitle());

        // 일치 검사
        boolean hasCommonKeyword = queryKeywords.stream()
                .anyMatch(keyword -> titleKeywords.stream()
                        .anyMatch(titleWord -> titleWord.contains(keyword) || keyword.contains(titleWord)));

        if (!queryKeywords.isEmpty() && !titleKeywords.isEmpty() && !hasCommonKeyword) {
            String warningMessage = "주의: 요청하신 레시피(" + String.join(", ", queryKeywords) + ")와 " +
                    "생성된 레시피(" + guide.getTitle() + ")가 일치하지 않을 수 있습니다.";

            logger.warn("쿼리와 레시피 불일치 감지. 쿼리 키워드: {}, 제목 키워드: {}",
                    queryKeywords, titleKeywords);

            return warningMessage;
        }

        return null;
    }

    /**
     * 텍스트에서 음식 관련 키워드를 추출합니다.
     */
    private List<String> extractFoodKeywords(String text) {
        if (text == null || text.isEmpty()) {
            return Collections.emptyList();
        }

        // 일반적인 음식 관련 키워드 추출
        Pattern foodPattern = Pattern.compile(
                "(김치찌개|된장찌개|비빔밥|불고기|떡볶이|파스타|스파게티|리조또|카레|피자|샐러드|볶음밥|김밥|라면|찜닭)",
                Pattern.CASE_INSENSITIVE);

        Matcher matcher = foodPattern.matcher(text);
        List<String> keywords = new ArrayList<>();

        while (matcher.find()) {
            keywords.add(matcher.group(1).toLowerCase());
        }

        return keywords;
    }
}