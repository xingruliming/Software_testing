package com.example.demo.controller;

import com.example.demo.commom.Result;
import com.example.demo.service.CaseService;
import jakarta.annotation.Resource;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;


@RestController
@RequestMapping("/upload")
public class CaseController {

    @Resource
    private CaseService caseService;


    // 定义文件上传的 POST 路由
    @PostMapping
    public Result<?> upload(@RequestParam("files") MultipartFile[] files,
                         @RequestParam("userId") Integer userId,
                         @RequestParam("demandId") Integer demandId) {

        return caseService.upload(files,userId,demandId);
    }

    @GetMapping
    public Result<?> ListFiles(@RequestParam("identity") String identity,@RequestParam("id") Integer id) {
        return caseService.listFiles(identity,id);
    }

    @GetMapping("/{fileId}")
    public ResponseEntity<FileSystemResource> downloadFile(@PathVariable Integer fileId){

        return caseService.download(fileId);
    }

    @PutMapping("/{id}")
    public Result<?> updateFile(@PathVariable Integer id){
        return caseService.update(id);
    }
}
