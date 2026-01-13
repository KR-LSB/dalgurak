package springbootApplication.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import springbootApplication.domain.User;
import springbootApplication.repository.UserRepository;

import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/users")
public class UserListController {

    @Autowired
    private UserRepository userRepository;

    @GetMapping("/list")
    public ResponseEntity<List<UserInfo>> getAllUsers() {
        List<UserInfo> users = userRepository.findAll().stream()
            .map(user -> new UserInfo(
                user.getUserId(),
                user.getUsername(),
                user.getEmail()
            ))
            .collect(Collectors.toList());
        
        return ResponseEntity.ok(users);
    }

    // 클라이언트에 반환할 간단한 사용자 정보 클래스
    public static class UserInfo {
        private Long id;
        private String username;
        private String email;

        public UserInfo(Long id, String username, String email) {
            this.id = id;
            this.username = username;
            this.email = email;
        }

        public Long getId() {
            return id;
        }

        public String getUsername() {
            return username;
        }

        public String getEmail() {
            return email;
        }
    }
}