package com.example.demo.controller;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.demo.commom.Result;
import com.example.demo.entity.Announcement;
import com.example.demo.entity.User;
import com.example.demo.service.AnnouncementService;
import com.example.demo.service.CompanyService;
import com.example.demo.service.UserService;
import jakarta.annotation.Resource;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/client")
public class ClientController {

    @Resource
    private UserService userservice;
    @Resource
    private AnnouncementService announcementService;
    @Resource
    private CompanyService companyService;

    @PutMapping("personal")
    public Result<?> changePassword(@RequestBody User user) {

        return userservice.changePassword(user);
    }

    @GetMapping("announcement")
    public Result<?> find(@RequestParam(defaultValue = "1") Integer pageNum,
                          @RequestParam(defaultValue = "10") Integer pageSize,
                          @RequestParam String state,
                          @RequestParam(required = false) String title,
                          @RequestParam(required = false) String time) {

        Page<Announcement> resultPage = announcementService.findSpecificAnnouncements(pageNum, pageSize, state, title, time);
        return Result.success(resultPage);

    }

    @GetMapping("requirement")
    public Result<?> requirement(@RequestParam String state) {
        return companyService.published_Requirement(state);
    }

}
