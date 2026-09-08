package com.example.demo.service;

import cn.hutool.core.io.resource.UrlResource;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.example.demo.commom.Result;
import com.example.demo.entity.Case;
import com.example.demo.entity.Requirement;
import com.example.demo.entity.User;
import com.example.demo.entity.fileConnected;
import com.example.demo.mapper.CaseMapper;
import com.example.demo.mapper.CompanyMapper;
import com.example.demo.mapper.UserMapper;
import com.example.demo.mapper.fileConnectedMapper;
import jakarta.annotation.Resource;

import org.springframework.core.io.FileSystemResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.net.MalformedURLException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

@Service
public class CaseService {

    @Resource
    private CaseMapper caseMapper;

    @Resource
    private UserMapper userMapper;

    @Resource
    private CompanyMapper companyMapper;

    @Resource
    private fileConnectedMapper fileconnectedMapper;

    public Result<?> upload(MultipartFile[] files, Integer userId, Integer demandId ) {
        if (files == null || files.length == 0) {
            return Result.error("-1","此文件为空");
        }

        // 获取当前项目的根目录，并设置上传文件的绝对路径
        String uploadDir = System.getProperty("user.dir") + File.separator + "uploads" + File.separator;

        // 创建上传目录（如果不存在）
        File directory = new File(uploadDir);
        if (!directory.exists()) {
            boolean isCreated = directory.mkdirs();
            if (isCreated) {
                System.out.println("Directory created successfully.");
            } else {
                System.out.println("Failed to create directory.");
                return Result.error("-2","创建目录失败");
            }
        }

        for (MultipartFile multipartFile : files) {

            Case existingcase = caseMapper.selectOne(Wrappers.<Case>lambdaQuery()
                                                    .eq(Case::getUserId, userId)
                    .eq(Case::getDemandId, demandId)
                    .eq(Case::getFileName, Objects.requireNonNull(multipartFile.getOriginalFilename()).replaceAll("[\\\\/:*?\"<>|]", "_")));

            if(existingcase != null) {
                return Result.error("-3", "上传重复文件：" + Objects.requireNonNull(multipartFile.getOriginalFilename()).replaceAll("[\\\\/:*?\"<>|]", "_"));
            }
            try {
                // 获取文件名并替换非法字符
                String originalFileName = multipartFile.getOriginalFilename();
                if (originalFileName == null) {
                    return Result.error("-4","非法文件名");
                }
                String fileName = originalFileName.replaceAll("[\\\\/:*?\"<>|]", "_");

                // 构建文件路径
                String filePath = uploadDir + fileName;

                // 存储文件到服务器
                multipartFile.transferTo(new File(filePath));

                // 创建数据库记录
                Case newCase = new Case();
                newCase.setFileName(originalFileName);
                newCase.setFilePath(filePath);
                newCase.setFileType(Files.probeContentType(Paths.get(filePath)));
                newCase.setFileSize(multipartFile.getSize()*1.0);
                newCase.setUserId(userId);
                newCase.setDemandId(demandId);

                Requirement requirement_ = companyMapper.selectById(demandId);
                newCase.setCompanyId(requirement_.getUserId());

                // 保存到数据库
                caseMapper.insert(newCase);

                fileConnected fc = new fileConnected();
                fc.setFilename(originalFileName);
                fc.setFilesize(multipartFile.getSize()*1.0);
                User user = userMapper.selectById(userId);
                fc.setUsername(user.getUsername());
                Requirement requirement = companyMapper.selectById(demandId);
                fc.setDemandname(requirement.getTitle());
                fc.setFilepath(filePath);
                fc.setPass("false");

                Case existing = caseMapper.selectOne(Wrappers.<Case>lambdaQuery()
                        .eq(Case::getUserId, userId)
                        .eq(Case::getDemandId, demandId)
                        .eq(Case::getFileName, Objects.requireNonNull(multipartFile.getOriginalFilename()).replaceAll("[\\\\/:*?\"<>|]", "_")));
                fc.setFileid(existing.getId());

                fileconnectedMapper.insert(fc);

            } catch (IOException e) {
                System.out.println("File upload failed: " + e.getMessage());
                return Result.error("-5",e.getMessage());
            }
        }
        System.out.println("File uploaded successfully.");
        return Result.success();

    }

    public Result<?> listFiles(String identity,Integer id) {
        List<fileConnected> list = new ArrayList<>();
        if(Objects.equals(identity, "管理员")) {
            list = fileconnectedMapper.selectList(null);
        }
        else if(Objects.equals(identity, "企业")){
            List<Case> clist = caseMapper.selectList(Wrappers.<Case>lambdaQuery().eq(Case::getCompanyId, id));
            List<Integer> ilist = new ArrayList<>();
            for(Case c : clist) {
                ilist.add(c.getId());
            }
            for(Integer i : ilist) {
                fileConnected fc = fileconnectedMapper.selectOne(Wrappers.<fileConnected>lambdaQuery()
                        .eq(fileConnected::getFileid, i));
                if(fc.getPass().equals("true")) {
                    list.add(fc);
                }

            }
        }

        return Result.success(list);
    }

    public ResponseEntity<FileSystemResource> download(Integer fileid) {
        // 查询数据库，获取文件路径
        Case fileRecord = caseMapper.selectById(fileid);
        if (fileRecord == null) {
            // 文件记录不存在，返回 404 错误
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(null);
        }

        try {
            // 获取文件路径
            Path filePath = Paths.get(fileRecord.getFilePath());

            // 创建 FileSystemResource 对象
            FileSystemResource resource = new FileSystemResource(filePath);

            // 检查文件是否存在且可读
            if (Files.exists(filePath) && Files.isReadable(filePath)) {
                // 文件名 URL 编码，防止特殊字符问题
                String encodedFileName = URLEncoder.encode(fileRecord.getFileName(), StandardCharsets.UTF_8);
                encodedFileName = encodedFileName.replace("+", "%20");
                // 设置响应头并返回文件
                return ResponseEntity.ok()
                        .contentType(MediaType.APPLICATION_OCTET_STREAM)  // 设置文件下载的 MIME 类型 表示文件是二进制流
                        .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + encodedFileName + "\"")//提示浏览器下载该文件，并使用 encodedFileName 作为文件名
                        .body(resource);//响应体包含了实际的文件内容，即 resource 指向的文件
            } else {
                // 文件不存在或不可读，返回 404 错误
                return ResponseEntity.status(HttpStatus.NOT_FOUND).body(null);
            }
        } catch (Exception e) {
            // 异常处理，返回 500 错误
            e.printStackTrace();  // 可以改为日志记录
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(null);
        }
    }

    public Result<?> update(Integer Id) {

        fileConnected fc = fileconnectedMapper.selectById(Id);
        fc.setPass("true");
        fileconnectedMapper.updateById(fc);
        return Result.success();
    }

}
