package springbootApplication.exception;

import java.io.Serializable;

public class ResourceNotFoundException extends RuntimeException implements Serializable {
    private static final long serialVersionUID = 1L;

    public ResourceNotFoundException(String message) {
        super(message);
    }
}