package springbootApplication.exception;

import java.io.Serializable;

public class UserIdAlreadyInUseException extends RuntimeException implements Serializable {
    private static final long serialVersionUID = 1L;

    public UserIdAlreadyInUseException(String message) {
        super(message);
    }
}