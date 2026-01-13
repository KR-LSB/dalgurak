package springbootApplication.service;

import lombok.RequiredArgsConstructor;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import springbootApplication.repository.UserRepository;  // UserRepository import
import springbootApplication.domain.User;  // User import

import java.util.List;

@Service
@RequiredArgsConstructor
public class ScheduledTaskService {

    private final UserRepository userRepository;  // UserRepository 사용
    private final WebPushService webPushService;

    // 매주 사용자에게 알림 보내기
    @Scheduled(cron = "0 0 9 * * MON")
    public void sendWeeklyMenuRecommendation() {
        List<User> allUsers = userRepository.findAll();  // 모든 사용자 조회

        for (User user : allUsers) {
            // 사용자별 푸시 알림 정보
            String endpoint = user.getPushNotificationEndpoint();
            String auth = user.getPushNotificationAuth();
            String p256dh = user.getPushNotificationP256dh();

            // 알림 메시지 작성
            String message = "오늘의 메뉴 추천: 일주일에 한 번씩!";

            // 푸시 알림 전송
            webPushService.sendPushNotification(endpoint, message, auth, p256dh);
        }
    }
}
