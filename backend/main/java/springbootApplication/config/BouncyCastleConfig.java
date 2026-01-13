package springbootApplication.config;

import org.bouncycastle.jce.provider.BouncyCastleProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.security.Security;

@Configuration
public class BouncyCastleConfig {

    @Bean
    public BouncyCastleProvider bouncyCastleProvider() {
        // BC 프로바이더가 이미 등록되어 있는지 확인
        if (Security.getProvider("BC") == null) {
            BouncyCastleProvider provider = new BouncyCastleProvider();
            Security.addProvider(provider);
            System.out.println("Bouncy Castle 공급자가 등록되었습니다.");
            return provider;
        }
        
        System.out.println("Bouncy Castle 공급자가 이미 등록되어 있습니다.");
        return (BouncyCastleProvider) Security.getProvider("BC");
    }
}