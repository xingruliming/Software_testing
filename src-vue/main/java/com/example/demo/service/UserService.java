package com.example.demo.service;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.example.demo.commom.Result;
import com.example.demo.entity.User;
import com.example.demo.mapper.UserMapper;
import jakarta.annotation.Resource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class UserService {

    @Resource
    private UserMapper usermapper;

    public Result<?> saveUser(User user) {
        User res = usermapper.selectOne(Wrappers.<User>lambdaQuery().eq(User::getUsername, user.getUsername()));
        if(res != null) {
            return Result.error("-1", "用户名已存在");
        }
        else{
            usermapper.insert(user);
            return Result.success();
        }

    }

    public void updateUser(User user) {
        usermapper.updateById(user);
    }

    public void deleteUser(Long id) {
        usermapper.deleteById(id);
    }

    public Result<?> login(User user) {
        // 先根据用户名查找用户
        User res = usermapper.selectOne(Wrappers.<User>lambdaQuery().eq(User::getUsername, user.getUsername()));

        // 如果用户不存在
        if (res == null) {
            return Result.error("-1", "用户名不存在");
        }

        // 如果用户名存在，但密码不匹配
        if (!res.getPassword().equals(user.getPassword())) {
            return Result.error("-1", "密码错误");
        }

        if (!res.getIdentity().equals(user.getIdentity())) {
            return Result.error("-1", "身份不匹配");
        }

        // 用户名和密码都正确
        System.out.println(res.getId());  // 输出并换行

        return Result.success(res.getId());
    }

    public Result<?> register(User user) {
        if(user.getUsername() == null){
            return Result.error("-1", "请填写用户名");
        }
        if(user.getPassword() == null){
            return Result.error("-1", "请填写密码");
        }
        if(user.getIdentity() == null){
            return Result.error("-1", "请选择身份");
        }
        User res = usermapper.selectOne(Wrappers.<User>lambdaQuery().eq(User::getUsername, user.getUsername()));
        if(res != null) {
            return Result.error("-1", "用户名已存在");
        }
        else{
            usermapper.insert(user);
        }
        return Result.success();
    }

    public User findUserIdByUsername(String username) {
        User res = usermapper.selectOne(Wrappers.<User>lambdaQuery().eq(User::getUsername, username));

        if(res != null) {
            return res;
        }
        else{
            return null;
        }
    }

    public Result<?> changePassword(User user) {
        User res = usermapper.selectOne(Wrappers.<User>lambdaQuery().eq(User::getId,user.getId()));
        if(res != null) {
            usermapper.updateById(user);
            return Result.success(user.getPassword());
        }
        else{
            return Result.error("-1", "not——ok");
        }
    }
}
