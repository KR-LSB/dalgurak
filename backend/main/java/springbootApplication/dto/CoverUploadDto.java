package springbootApplication.dto;

import lombok.Data;
import springbootApplication.domain.Cover;
import org.springframework.web.multipart.MultipartFile;


@Data
public class CoverUploadDto {
    private MultipartFile file;
	
	public Cover toEntity(String coverImageUrl) {
		return Cover.builder()
				.coverImageUrl(coverImageUrl)
				.build();
	}
}