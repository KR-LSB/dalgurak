package springbootApplication.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.LinkedList;
import java.util.concurrent.locks.ReentrantReadWriteLock;

@Service
public class QueryHistoryService {
    private static final Logger logger = LoggerFactory.getLogger(QueryHistoryService.class);

    // 마지막 10개 성공 쿼리 저장 (FIFO)
    private final LinkedList<String> lastSuccessfulQueries = new LinkedList<>();
    private final int MAX_HISTORY_SIZE = 10;

    // 스레드 안전 확보
    private final ReentrantReadWriteLock lock = new ReentrantReadWriteLock();

    /**
     * 성공적인 쿼리 저장
     */
    public void saveSuccessfulQuery(String query) {
        if (query == null || query.trim().isEmpty() || query.trim().length() < 2) {
            return;
        }

        String trimmedQuery = query.trim();

        // 쓰기 락 획득
        lock.writeLock().lock();
        try {
            // 중복 제거 (이미 있으면 삭제 후 다시 추가)
            lastSuccessfulQueries.remove(trimmedQuery);

            // 최신 쿼리를 맨 앞에 추가
            lastSuccessfulQueries.addFirst(trimmedQuery);

            // 최대 크기 유지
            if (lastSuccessfulQueries.size() > MAX_HISTORY_SIZE) {
                lastSuccessfulQueries.removeLast();
            }

            logger.info("성공한 쿼리 저장: {}", trimmedQuery);
        } finally {
            // 락 해제
            lock.writeLock().unlock();
        }
    }

    /**
     * 마지막으로 성공한 쿼리 조회
     */
    public String getLastSuccessfulQuery() {
        lock.readLock().lock();
        try {
            if (!lastSuccessfulQueries.isEmpty()) {
                return lastSuccessfulQueries.getFirst();
            }
        } finally {
            lock.readLock().unlock();
        }

        return "인기 레시피 추천해줘";
    }

    /**
     * 유효한 쿼리인지 검증
     */
    public boolean isValidQuery(String query) {
        if (query == null || query.trim().isEmpty()) {
            return false;
        }

        String trimmedQuery = query.trim();
        return trimmedQuery.length() >= 2 &&
                !trimmedQuery.contains("[") &&
                !trimmedQuery.contains("]");
    }
}