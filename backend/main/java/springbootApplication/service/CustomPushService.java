package springbootApplication.service;

import org.apache.http.HttpResponse;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.entity.StringEntity;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class CustomPushService { 
    private final String publicKey;
    private final String privateKey;
    private final String subject;
    private final CloseableHttpClient httpClient;

    public CustomPushService(
            @Value("${vapid.publicKey}") String publicKey, 
            @Value("${vapid.privateKey}") String privateKey, 
            @Value("${vapid.subject}") String subject, 
            CloseableHttpClient httpClient) {
        this.publicKey = publicKey;
        this.privateKey = privateKey;
        this.subject = subject;
        this.httpClient = httpClient;
    }

    public HttpResponse send(String endpoint, String message, String auth, String p256dh) {
        HttpPost httpPost = new HttpPost(endpoint);
        
        // JSON 페이로드에 웹푸시 관련 정보 포함
        String jsonBody = String.format(
            "{\"message\":\"%s\",\"auth\":\"%s\",\"p256dh\":\"%s\",\"publicKey\":\"%s\",\"subject\":\"%s\"}", 
            message, auth, p256dh, publicKey, subject
        );

        try {
            StringEntity entity = new StringEntity(jsonBody);
            httpPost.setEntity(entity);
            httpPost.setHeader("Content-Type", "application/json");

            // 주입된 httpClient 사용하여 요청 실행
            return httpClient.execute(httpPost);
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }
}