package com.example.demo.service;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.example.demo.commom.Result;
import com.example.demo.entity.Invite;
import com.example.demo.entity.User;
import com.example.demo.mapper.InviteMapper;
import jakarta.annotation.Resource;
import jakarta.persistence.criteria.CriteriaBuilder;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class InviteService {
    @Resource
    private InviteMapper inviteMapper;

    public Result<?> invite(Invite invite) {
        Invite invite1 = inviteMapper.selectOne(Wrappers.<Invite>lambdaQuery()
                .eq(Invite::getUserId,invite.getUserId())
                .eq(Invite::getCompanyId,invite.getCompanyId()));
        if (invite1 != null && Objects.equals(invite1.getState(), "invited")) {
            return Result.error("-1","已发送邀请！");
        }
        else if(invite1 != null && Objects.equals(invite1.getState(), "accepted")){
            return Result.error("-3","该用户已接受邀请！");
        }
        else if(invite1 != null && Objects.equals(invite1.getState(), "rejected")){
            return Result.error("-2","该用户已拒绝邀请！");
        }
        inviteMapper.insert(invite);
        return Result.success();
    }

    public Result<?> getAll(Integer id){
        List<Invite> invites = inviteMapper.selectList(Wrappers.<Invite>lambdaQuery().eq(Invite::getUserId,id).eq(Invite::getState,"invited"));
        return Result.success(invites);
    }

    public Result<?> select(Invite invite){
        inviteMapper.updateById(invite);
        return Result.success();
    }
}
