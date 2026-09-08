package com.example.demo.controller;

import com.example.demo.commom.Result;
import com.example.demo.entity.User;
import com.example.demo.service.UserService;
import jakarta.annotation.Resource;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;


@RestController
@RequestMapping("/register")

public class RegisterController {


        @Resource
        private UserService userservice;

        @PostMapping//
        public Result<?> register(@RequestBody User user) {

            return userservice.register(user);
        }


}
