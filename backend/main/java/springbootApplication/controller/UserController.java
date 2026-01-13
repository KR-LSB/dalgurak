package springbootApplication.controller;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.logout.SecurityContextLogoutHandler;
import org.springframework.web.bind.annotation.*;
import springbootApplication.domain.User;
import springbootApplication.dto.AddUserRequest;
import springbootApplication.service.UserService;
import io.swagger.v3.oas.annotations.tags.Tag;
import io.swagger.v3.oas.annotations.Operation;
import java.util.List;

@RestController
@RequestMapping("/api/users")
@Tag(name = "User Management", description = "Operations related to user management")
@RequiredArgsConstructor
public class UserController {
    private final UserService userService;

    // 회원가입
    @PostMapping("/signup")
    @Operation(summary = "회원가입", description = "새로운 사용자 등록")
    public ResponseEntity<String> signup(@Valid @RequestBody AddUserRequest request) {
        try {
            // request에서 username과 phoneNumber 가져오기
            User user = User.builder()
                    .email(request.getEmail())
                    .username(request.getUsername() != null ? request.getUsername() : request.getEmail()) // username이 없으면 email 사용
                    .phoneNumber(request.getPhoneNumber())
                    .password(request.getPassword()) // UserService에서 암호화됨
                    .build();
            
            Long userId = userService.save(user);
            return ResponseEntity.ok("회원가입이 완료되었습니다. 사용자 ID: " + userId);
        } catch (Exception e) {
            return ResponseEntity.badRequest().body("회원가입 실패: " + e.getMessage());
        }
    }

    // 로그아웃
    @GetMapping("/logout")
    @Operation(summary = "로그아웃", description = "현재 사용자 로그아웃")
    public ResponseEntity<String> logout(HttpServletRequest request, HttpServletResponse response) {
        SecurityContextLogoutHandler logoutHandler = new SecurityContextLogoutHandler();
        logoutHandler.logout(request, response, SecurityContextHolder.getContext().getAuthentication());
        return ResponseEntity.ok("로그아웃 되었습니다.");
    }

    // 유저 생성
    @PostMapping
    @Operation(summary = "사용자 생성", description = "새로운 사용자 계정 생성")
    public ResponseEntity<User> createUser(@RequestBody User user) {
        User createdUser = userService.createUser(user);
        return ResponseEntity.ok(createdUser);
    }

    // 모든 유저 조회
    @GetMapping
    @Operation(summary = "전체 사용자 조회", description = "모든 사용자 목록 조회")
    public ResponseEntity<List<User>> getAllUsers() {
        List<User> users = userService.getAllUsers();
        return ResponseEntity.ok(users);
    }

    // 유저 정보 수정
    @PutMapping("/{id}")
    @Operation(summary = "사용자 정보 수정", description = "특정 사용자의 정보 업데이트")
    public ResponseEntity<User> updateUser(@PathVariable Long id, @RequestBody User userDetails) {
        User updatedUser = userService.updateUser(id, userDetails);
        return ResponseEntity.ok(updatedUser);
    }

    // 유저 삭제
    @DeleteMapping("/{id}")
    @Operation(summary = "사용자 삭제", description = "특정 사용자 계정 삭제")
    public ResponseEntity<Void> deleteUser(@PathVariable Long id) {
        userService.deleteUser(id);
        return ResponseEntity.noContent().build();
    }
}