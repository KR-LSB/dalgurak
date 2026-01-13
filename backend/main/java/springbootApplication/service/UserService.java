package springbootApplication.service;

import org.springframework.stereotype.Service;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.transaction.annotation.Transactional;
import springbootApplication.exception.EmailAlreadyInUseException;
import springbootApplication.repository.UserRepository;
import springbootApplication.domain.User;
import springbootApplication.dto.AddUserRequest;

import lombok.RequiredArgsConstructor;

import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class UserService {
    private final UserRepository userRepository;
    private final BCryptPasswordEncoder bCryptPasswordEncoder;

    @Transactional
    public Long save(User user) {
        if (userRepository.existsByEmail(user.getEmail())) {
            throw new EmailAlreadyInUseException("이미 사용 중인 이메일입니다.");
        }
        
        user.setPassword(bCryptPasswordEncoder.encode(user.getPassword()));
        return userRepository.save(user).getUserId();
    }

    @Transactional
    public Long save(AddUserRequest dto) {
        if (userRepository.existsByEmail(dto.getEmail())) {
            throw new EmailAlreadyInUseException("이미 사용 중인 이메일입니다.");
        }

        User user = User.builder()
                .email(dto.getEmail())
                .username(dto.getUsername() != null ? dto.getUsername() : dto.getEmail())
                .phoneNumber(dto.getPhoneNumber())
                .build();
        
        user.setPassword(bCryptPasswordEncoder.encode(dto.getPassword()));
        return userRepository.save(user).getUserId();
    }

    public List<User> getAllUsers() {
        return userRepository.findAll();
    }

    public Optional<User> getUserById(Long id) {
        return userRepository.findById(id);
    }

    public User createUser(User user) {
        if (userRepository.existsByEmail(user.getEmail())) {
            throw new EmailAlreadyInUseException("이미 사용 중인 이메일입니다.");
        }
        user.setPassword(bCryptPasswordEncoder.encode(user.getPassword()));
        return userRepository.save(user);
    }

    public User updateUser(Long id, User updatedDetails) {
        Optional<User> existingUserOpt = userRepository.findById(id);
        if (!existingUserOpt.isPresent()) {
            throw new RuntimeException("User not found with id: " + id);
        }

        // 이메일 중복 체크 (기존 이메일과 다른 경우에만)
        User existingUser = existingUserOpt.get();
        if (!existingUser.getEmail().equals(updatedDetails.getEmail()) && 
            userRepository.existsByEmail(updatedDetails.getEmail())) {
            throw new EmailAlreadyInUseException("이미 사용 중인 이메일입니다.");
        }

        existingUser.setUsername(updatedDetails.getUsername());
        existingUser.setEmail(updatedDetails.getEmail());
        existingUser.setPassword(bCryptPasswordEncoder.encode(updatedDetails.getPassword()));

        return userRepository.save(existingUser);
    }

    public void deleteUser(Long id) {
        if (!userRepository.existsById(id)) {
            throw new RuntimeException("User not found with id: " + id);
        }
        userRepository.deleteById(id);
    }
}