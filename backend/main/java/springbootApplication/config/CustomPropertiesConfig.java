package springbootApplication.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import lombok.Getter;
import lombok.Setter;

@Configuration
@ConfigurationProperties(prefix = "custom")
@Getter
@Setter
public class CustomPropertiesConfig {
    private File file;
    private Vapid vapid;

    @Getter
    @Setter
    public static class File {
        private String path;
    }

    @Getter
    @Setter
    public static class Vapid {
        private String publicKey;
        private String privateKey;
        private String subject;
    }
}