package springbootApplication.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import java.util.HashMap;
import java.util.Map;

@RestController
public class LoginController {
    
    @PostMapping("/api/auth/login")
    public ResponseEntity<?> login(@RequestBody LoginRequest loginRequest) {
        // 여기에 실제 인증 로직 구현 (이메일/비밀번호 검증 등)
        
        // 사용자 정보를 담을 맵 생성
        Map<String, Object> user = new HashMap<>();
        user.put("id", "user123"); // 실제로는 DB에서 가져온 ID
        user.put("username", "사용자명"); // 실제로는 DB에서 가져온 이름
        user.put("email", loginRequest.getEmail());
        
        // 사용자 기본 설정 정보
        Map<String, Object> preferences = new HashMap<>();
        preferences.put("spicyLevel", "보통");
        preferences.put("cookingTime", 30);
        preferences.put("vegetarian", false);
        user.put("preferences", preferences);
        
        // 전체 응답 구성
        Map<String, Object> response = new HashMap<>();
        response.put("token", "JWT_TOKEN_HERE"); // 실제로는 JWT 토큰 생성 로직 필요
        response.put("user", user);
        
        return ResponseEntity.ok(response);
    }
}

class LoginRequest {
    private String email;
    private String password;
    
    // 기본 생성자
    public LoginRequest() {}
    
    // 게터와 세터
    public String getEmail() {
        return email;
    }
    
    public void setEmail(String email) {
        this.email = email;
    }
    
    public String getPassword() {
        return password;
    }
    
    public void setPassword(String password) {
        this.password = password;
    }
}