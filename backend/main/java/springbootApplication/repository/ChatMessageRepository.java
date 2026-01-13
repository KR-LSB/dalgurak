package springbootApplication.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import springbootApplication.model.ChatMessage;

import java.util.List;
import java.util.Optional;

@Repository
public interface ChatMessageRepository extends JpaRepository<ChatMessage, Long> {
    /**
     * 특정 ID보다 큰 ID를 가진 메시지 중 특정 발신자의 첫 번째 메시지를 찾습니다.
     * AI 응답을 찾기 위해 사용됩니다.
     *
     * @param id 기준 ID
     * @param sender 발신자
     * @return 찾은 메시지 (Optional)
     */
    Optional<ChatMessage> findTopByIdGreaterThanAndSenderOrderByIdAsc(Long id, String sender);

    /**
     * 메시지 내용에 특정 문자열이 포함된 모든 메시지를 찾습니다.
     *
     * @param content 찾을 내용
     * @return 찾은 메시지 목록
     */
    List<ChatMessage> findByMessageContaining(String content);

    /**
     * 특정 발신자가 보낸 메시지 중 특정 내용이 포함된 모든 메시지를 찾습니다.
     *
     * @param sender 발신자
     * @param content 찾을 내용
     * @return 찾은 메시지 목록
     */
    List<ChatMessage> findBySenderAndMessageContaining(String sender, String content);

    /**
     * 특정 메시지 내용과 정확히 일치하는 메시지를 찾습니다.
     *
     * @param message 찾을 메시지 내용
     * @return 찾은 메시지 (Optional)
     */
    Optional<ChatMessage> findByMessage(String message);

    /**
     * 특정 발신자의 가장 최근 메시지를 찾습니다.
     *
     * @param sender 발신자
     * @return 찾은 메시지 (Optional)
     */
    Optional<ChatMessage> findTopBySenderOrderByIdDesc(String sender);
}