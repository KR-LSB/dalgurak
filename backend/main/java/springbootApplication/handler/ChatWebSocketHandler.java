package springbootApplication.handler;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import springbootApplication.dto.ChatMessageDto;

import java.util.concurrent.CopyOnWriteArraySet;

public class ChatWebSocketHandler extends TextWebSocketHandler {

    private static final CopyOnWriteArraySet<WebSocketSession> sessions = new CopyOnWriteArraySet<>();
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        sessions.add(session);
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        ChatMessageDto chatMessage = objectMapper.readValue(message.getPayload(), ChatMessageDto.class);
        broadcast(chatMessage);
    }

    private void broadcast(ChatMessageDto message) throws Exception {
        String jsonMessage = objectMapper.writeValueAsString(message);
        for (WebSocketSession session : sessions) {
            session.sendMessage(new TextMessage(jsonMessage));
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, org.springframework.web.socket.CloseStatus status) {
        sessions.remove(session);
    }
}