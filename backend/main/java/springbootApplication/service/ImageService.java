package springbootApplication.service;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import lombok.RequiredArgsConstructor;

import springbootApplication.domain.Cover;
import springbootApplication.dto.CoverUploadDto;
import springbootApplication.repository.CoverRepository;

@RequiredArgsConstructor
@Service
public class ImageService {

    private final CoverRepository coverRepository;

    @Value("${file.path}")
    private String uploadFolder;

    @Transactional
    public void coverImageUpload(CoverUploadDto coverUploadDto) {
        try {
            // 디렉토리가 존재하는지 확인하고 없으면 생성
            Path uploadDir = Paths.get(uploadFolder);
            if (!Files.exists(uploadDir)) {
                Files.createDirectories(uploadDir);
            }
            
            UUID uuid = UUID.randomUUID();
            String imageFileName = uuid + "_" + coverUploadDto.getFile().getOriginalFilename();
            System.out.println("커버 이미지 파일이름:" + imageFileName);

            Path imageFilePath = Paths.get(uploadFolder + imageFileName);

            Files.write(imageFilePath, coverUploadDto.getFile().getBytes());
            
            Cover cover = coverUploadDto.toEntity(imageFileName);
            coverRepository.save(cover);
        } catch (Exception e) {
            e.printStackTrace();
            throw new RuntimeException("이미지 업로드 중 오류가 발생했습니다: " + e.getMessage());
        }
    }
}