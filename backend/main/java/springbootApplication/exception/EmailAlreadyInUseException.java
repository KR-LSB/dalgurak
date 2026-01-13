package springbootApplication.exception;

import java.io.Serializable;

public class EmailAlreadyInUseException extends RuntimeException implements Serializable {
    private static final long serialVersionUID = 1L;

    public EmailAlreadyInUseException(String message) {
        super(message);
    }
}