package springbootApplication.model;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "chat_messages")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ChatMessage {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(columnDefinition = "TEXT")
    private String message;

    private String sender;

    @Column(name = "created_at")
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    // 컨텍스트 타입 추가 (AI, USER 등)
    @Enumerated(EnumType.STRING)
    @Column(name = "message_type")
    private MessageType messageType;

    public enum MessageType {
        USER, AI, SYSTEM
    }
}