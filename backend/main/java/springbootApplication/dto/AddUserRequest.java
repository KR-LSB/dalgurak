package springbootApplication.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import lombok.Builder;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import jakarta.validation.constraints.Email;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder 
public class AddUserRequest {

    @NotNull(message = "Email cannot be null")
    @Email(message = "Email should be valid")
    private String email;
    
    @NotNull(message = "Password cannot be null")
    @Size(min = 6, message = "Password should be at least 6 characters long")
    private String password;
    
    private String username;
    
    @NotNull(message = "Phone number cannot be null")
    private String phoneNumber;
    
    public AddUserRequest(String email, String password) {
        this.email = email;
        this.password = password;
    }
}