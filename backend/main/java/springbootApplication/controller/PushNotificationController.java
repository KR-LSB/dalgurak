package springbootApplication.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import springbootApplication.dto.PushSubscriptionDto;
import springbootApplication.service.UserService;
import springbootApplication.service.WebPushService;
import springbootApplication.domain.User;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

import java.util.List;

@RestController
@RequestMapping("/api/push")
@RequiredArgsConstructor
@Tag(name = "Push Notifications", description = "웹 푸시 알림 관련 API")
public class PushNotificationController {

    private final UserService userService;
    private final WebPushService webPushService;

    @PostMapping("/subscribe/{userId}")
    @Operation(summary = "푸시 구독 정보 저장", description = "사용자의 푸시 알림 구독 정보를 저장합니다.")
    public ResponseEntity<?> savePushSubscription(
            @PathVariable Long userId,
            @RequestBody PushSubscriptionDto subscriptionDto) {
        
        try {
            User user = userService.getUserById(userId)
                    .orElseThrow(() -> new RuntimeException("사용자를 찾을 수 없습니다: " + userId));
            
            // 구독 정보를 사용자 엔티티에 저장
            user.setPushNotificationEndpoint(subscriptionDto.getEndpoint());
            user.setPushNotificationAuth(subscriptionDto.getAuth());
            user.setPushNotificationP256dh(subscriptionDto.getP256dh());
            
            userService.updateUser(userId, user);
            
            return ResponseEntity.ok("푸시 알림 구독 정보가 저장되었습니다.");
        } catch (Exception e) {
            return ResponseEntity.badRequest().body("푸시 알림 구독 정보 저장 실패: " + e.getMessage());
        }
    }

    @PostMapping("/test/{userId}")
    @Operation(summary = "푸시 알림 테스트", description = "특정 사용자에게 테스트 알림을 전송합니다.")
    public ResponseEntity<?> sendTestNotification(@PathVariable Long userId) {
        try {
            User user = userService.getUserById(userId)
                    .orElseThrow(() -> new RuntimeException("사용자를 찾을 수 없습니다: " + userId));
            
            // 테스트 알림 메시지
            String message = "안녕하세요! 달그락의 테스트 알림입니다. 현재 시간: " + java.time.LocalDateTime.now();
            
            // 구독 정보 확인
            System.out.println("전송 시도: " + message);
            System.out.println("Auth: " + user.getPushNotificationAuth());
            System.out.println("P256dh: " + user.getPushNotificationP256dh());
            
            if (user.getPushNotificationEndpoint() == null || 
                user.getPushNotificationAuth() == null || 
                user.getPushNotificationP256dh() == null) {
                return ResponseEntity.badRequest().body("푸시 알림 구독 정보가 없습니다.");
            }
            
            // 웹 푸시 서비스를 사용하여 알림 전송
            webPushService.sendPushNotification(
                    user.getPushNotificationEndpoint(),
                    user.getPushNotificationAuth(),
                    user.getPushNotificationP256dh(),
                    message
            );
            
            return ResponseEntity.ok("테스트 알림이 전송되었습니다.");
        } catch (Exception e) {
            return ResponseEntity.badRequest().body("테스트 알림 전송 실패: " + e.getMessage());
        }
    }
    
    @PostMapping("/send-to-all")
    @Operation(summary = "모든 사용자에게 알림 전송", description = "구독한 모든 사용자에게 알림을 전송합니다.")
    public ResponseEntity<?> sendNotificationToAll(@RequestBody String message) {
        try {
            // 모든 사용자 가져오기
            List<User> users = userService.getAllUsers();
            int successCount = 0;
            
            for (User user : users) {
                // 푸시 알림 구독 정보가 있는 사용자에게만 전송
                if (user.getPushNotificationEndpoint() != null && 
                    user.getPushNotificationAuth() != null && 
                    user.getPushNotificationP256dh() != null) {
                    
                    webPushService.sendPushNotification(
                        user.getPushNotificationEndpoint(),
                        user.getPushNotificationAuth(),
                        user.getPushNotificationP256dh(),
                        message
                    );
                    
                    successCount++;
                }
            }
            
            return ResponseEntity.ok(successCount + "명의 사용자에게 알림이 전송되었습니다.");
        } catch (Exception e) {
            return ResponseEntity.badRequest().body("알림 전송 실패: " + e.getMessage());
        }
    }
}