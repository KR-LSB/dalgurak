package springbootApplication.domain;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import java.sql.Timestamp;

@Entity
@Table(name = "cover") // 명시적으로 테이블명 지정
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Cover {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private int id;

    @Column(name = "cover_image_url", nullable = false, length = 255)
    private String coverImageUrl;

    @CreationTimestamp
    @Column(name = "create_date", nullable = false, updatable = false)
    private Timestamp createDate;
}
