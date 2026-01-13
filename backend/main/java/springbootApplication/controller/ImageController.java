package springbootApplication.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.PostMapping;
import springbootApplication.dto.CoverUploadDto;
import springbootApplication.service.ImageService;

@Controller
public class ImageController {

    private final ImageService imageService;

    public ImageController(ImageService imageService) {
        this.imageService = imageService;
    }
    
    @PostMapping("/")
    public String coverImageUpload(CoverUploadDto coverUploadDto) {
        if(coverUploadDto.getFile().isEmpty()) {
            throw new RuntimeException("이미지가 첨부되지 않았습니다.", null);
        }

        // 한글 메서드명을 영문 메서드명으로 변경하여 호출
        imageService.coverImageUpload(coverUploadDto);
        return "redirect:/";
    }
}