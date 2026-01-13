package springbootApplication.controller;

import springbootApplication.domain.CommunityPost;
import springbootApplication.service.CommunityPostService; 
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/community")
@Tag(name = "Community", description = "Manage community posts")
public class CommunityPostController {

    private final CommunityPostService communityPostService;

    public CommunityPostController(CommunityPostService communityPostService) {
        this.communityPostService = communityPostService;
    }

    @GetMapping
    @Operation(summary = "Get all community posts", description = "Retrieve all community posts")
    public List<CommunityPost> getAllPosts() {
        return communityPostService.getAllPosts();
    }


    @PostMapping
    @Operation(summary = "Create a new community post", description = "Add a new post to the community board")
    public ResponseEntity<CommunityPost> createPost(@RequestBody CommunityPost post) {
        try {
            CommunityPost createdPost = communityPostService.createPost(post);
            return ResponseEntity.status(HttpStatus.CREATED).body(createdPost); // 201 CREATED 반환
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).build();  // 잘못된 요청 처리
        }
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update a community post", description = "Update an existing community post")
    public ResponseEntity<CommunityPost> updatePost(@PathVariable Long id, @RequestBody CommunityPost updatedPost) {
        try {
            CommunityPost updated = communityPostService.updatePost(id, updatedPost);
            return ResponseEntity.ok(updated); // 200 OK 반환
        } catch (RuntimeException e) {
            return ResponseEntity.notFound().build();  // 포스트가 없을 때 404 처리
        }
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete a community post", description = "Delete a community post by ID")
    public ResponseEntity<Void> deletePost(@PathVariable Long id) {
        communityPostService.deletePost(id);
        return ResponseEntity.noContent().build(); // 204 No Content 반환
    }
}

