package springbootApplication.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;

@Service
public class PythonAIService {
    @Value("${python.executable.path:python}")
    private String pythonPath;

    @Value("${python.script.directory}")
    private String scriptDirectory;

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 기존 레시피 RAG 실행 메서드
     */
    public String executeRecipeRAG(String question) throws IOException, InterruptedException {
        ProcessBuilder processBuilder = new ProcessBuilder(
                pythonPath,
                "-u",      // Unbuffered output
                scriptDirectory + "/recipe_rag_script.py",
                question
        );

        // 환경 변수 설정
        Map<String, String> env = processBuilder.environment();
        env.put("PYTHONPATH", scriptDirectory);
        env.put("PYTHONIOENCODING", "utf-8");
        env.put("LANG", "ko_KR.UTF-8");

        Process process = processBuilder.start();

        // 결과 읽기
        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {

            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
            }
        }

        // 에러 확인
        int exitCode = process.waitFor();
        if (exitCode != 0) {
            StringBuilder error = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(process.getErrorStream(), StandardCharsets.UTF_8))) {

                String line;
                while ((line = reader.readLine()) != null) {
                    error.append(line).append("\n");
                }
            }
            throw new RuntimeException("Python 실행 오류: " + error.toString().trim());
        }

        String result = output.toString().trim();

        try {
            JsonNode rootNode = objectMapper.readTree(result);
            // data.answer 필드가 있는지 확인
            if (rootNode.has("data") && rootNode.get("data").has("answer")) {
                // 텍스트를 그대로 반환 (줄바꿈 유지)
                return rootNode.get("data").get("answer").asText();
            }
        } catch (Exception e) {
            // JSON 파싱 실패 시 원본 텍스트 반환
        }

        return result;
    }

    /**
     * 요리 가이드 채팅을 위한 Python 스크립트 실행 메서드
     *
     * @param prompt 완성된 프롬프트 텍스트
     * @param cookingContext 요리 컨텍스트 JSON 문자열 (옵션)
     * @return AI 응답 텍스트
     */
    public String executeCookingGuideRAG(String prompt, String cookingContext) throws IOException, InterruptedException {
        // 임시 파일 생성 (긴 프롬프트 처리를 위해)
        Path promptFile = createTempPromptFile(prompt);

        // Python 스크립트 실행 준비
        ProcessBuilder processBuilder = new ProcessBuilder(
                pythonPath,
                "-u",      // Unbuffered output
                scriptDirectory + "/cooking_guide_script.py",
                promptFile.toString(),
                cookingContext != null ? cookingContext : "{}"
        );

        // 환경 변수 설정
        Map<String, String> env = processBuilder.environment();
        env.put("PYTHONPATH", scriptDirectory);
        env.put("PYTHONIOENCODING", "utf-8");
        env.put("LANG", "ko_KR.UTF-8");

        // 프로세스 실행
        Process process = processBuilder.start();

        // 결과 읽기
        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {

            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
            }
        }

        // 임시 파일 삭제
        Files.deleteIfExists(promptFile);

        // 에러 확인
        int exitCode = process.waitFor();
        if (exitCode != 0) {
            StringBuilder error = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(process.getErrorStream(), StandardCharsets.UTF_8))) {

                String line;
                while ((line = reader.readLine()) != null) {
                    error.append(line).append("\n");
                }
            }
            throw new RuntimeException("Python 실행 오류: " + error.toString().trim());
        }

        String result = output.toString().trim();

        try {
            // JSON 응답 구조 확인
            JsonNode rootNode = objectMapper.readTree(result);
            if (rootNode.has("data") && rootNode.get("data").has("answer")) {
                return rootNode.get("data").get("answer").asText();
            }
        } catch (Exception e) {
            // JSON 파싱 실패 시 원본 텍스트 반환
        }

        return result;
    }

    /**
     * 프롬프트 내용을 임시 파일로 저장
     *
     * @param prompt 프롬프트 텍스트
     * @return 임시 파일 경로
     * @throws IOException 파일 생성 오류
     */
    private Path createTempPromptFile(String prompt) throws IOException {
        Path tempFile = Files.createTempFile("prompt_", ".txt");
        Files.write(tempFile, prompt.getBytes(StandardCharsets.UTF_8));
        return tempFile;
    }
}