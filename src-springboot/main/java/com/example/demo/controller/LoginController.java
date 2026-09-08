package com.example.demo.controller;

import com.example.demo.commom.Result;
import com.example.demo.entity.User;
import com.example.demo.mapper.UserMapper;
import com.example.demo.service.UserService;
import jakarta.annotation.Resource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/login")
public class LoginController {

    @Resource
    private UserService userservice;

    @PostMapping//新增
    public Result<?> login(@RequestBody User user) {

        return userservice.login(user);
    }


}
