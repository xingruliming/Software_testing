package com.example.demo.controller;
import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.demo.commom.Result;
import com.example.demo.entity.Announcement;
import com.example.demo.entity.User;
import com.example.demo.mapper.AnnouncementMapper;
import com.example.demo.mapper.UserMapper;
import com.example.demo.service.AnnouncementService;
import com.example.demo.service.UserService;
import jakarta.annotation.Resource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/home/announcement")
public class AnnouncementController {

    @Resource
    private AnnouncementService announcementService;

    @GetMapping
    public Result<?> find(@RequestParam(defaultValue = "1") Integer pageNum,
                          @RequestParam(defaultValue = "10") Integer pageSize,
                          @RequestParam(required = false) String state) {
        Page<Announcement> resultPage = announcementService.findAnnouncements(pageNum, pageSize,state);
        return Result.success(resultPage);
    }

    @PostMapping//
    public Result<?> create(@RequestBody Announcement announcement ) {

        announcementService.createAnnouncement(announcement);
        return Result.success();
    }

    @DeleteMapping//
    public Result<?> delete(@RequestBody List<Integer> ids) {

        announcementService.deleteAnnouncement(ids);
        return Result.success();
    }

    @PutMapping
    public Result<?> findSelected(@RequestBody List<Integer> ids) {

        return announcementService.findSelected(ids);

    }
}
