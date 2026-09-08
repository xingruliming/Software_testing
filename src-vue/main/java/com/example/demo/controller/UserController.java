package com.example.demo.controller;

import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.demo.commom.Result;
import com.example.demo.entity.User;
import com.example.demo.mapper.UserMapper;
import com.example.demo.service.UserService;
import jakarta.annotation.Resource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.sql.Wrapper;

@RestController
@RequestMapping("/home/user")
public class UserController {

    @Resource
    private UserService userservice;
    @Autowired
    private UserMapper userMapper;

    @PostMapping//新增
    public Result<?> save(@RequestBody User user) {
        if(user.getPassword() == null){
            user.setPassword("123456");
        }
        return userservice.saveUser(user);
    }


    @PutMapping//更新
    public Result<?> update(@RequestBody User user) {
        if(user.getPassword() == null){
            user.setPassword("123456");
        }
        userservice.updateUser(user);
        return Result.success();
    }

    @PutMapping("person")//更新
    public Result<?> update_person(@RequestBody User user) {

        userservice.updateUser(user);
        return Result.success();
    }

    @DeleteMapping("/{id}")//删除
    public Result<?> delete(@PathVariable Long id) {
        userservice.deleteUser(id);
        return Result.success();
    }

    @GetMapping//查询
    public Result<?> find(@RequestParam(defaultValue = "1") Integer pageNum,
                          @RequestParam(defaultValue = "5") Integer pageSize,
                          @RequestParam(defaultValue = "") String search) {
        Page<User> page = new Page<>(pageNum, pageSize);//创建一个 MyBatis-Plus 的分页对象。
        LambdaQueryWrapper<User> wrapper = Wrappers.<User>lambdaQuery();//创建一个条件构造器，用于动态拼接 SQL 查询条件
        if(StrUtil.isNotBlank(search)){
            wrapper.and(w -> w
                    .like(User::getNickName, search)
                    .or()
                    .like(User::getUsername, search)
            );
        }
        Page<User> resultPage=userMapper.selectPage(page,wrapper);//MyBatis-Plus 提供的分页查询方法。
        //page：分页对象，包含页码和页大小。
        //wrapper：条件构造器，用于指定查询条件。
        return Result.success(resultPage);
    }

    @GetMapping("person")//ch查询
    public Result<?> find_id(String username) {

        User res = userservice.findUserIdByUsername(username);
        if (res != null) {
            return Result.success(res); // 返回找到的用户 ID
        }
        else {
            return Result.error("-1","ID不存在"); // 返回错误信息
        }
    }


}
