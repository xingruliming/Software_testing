package com.example.demo.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.demo.commom.Result;
import com.example.demo.entity.Reply;
import com.example.demo.entity.ReplyDTO;
import com.example.demo.entity.Requirement;
import com.example.demo.entity.User;
import com.example.demo.mapper.CompanyMapper;
import com.example.demo.mapper.ReplyMapper;
import com.example.demo.mapper.UserMapper;
import jakarta.annotation.Resource;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.RequestBody;

import java.util.ArrayList;
import java.util.List;

@Service
public class ReplyService {
    @Resource
    private ReplyMapper replyMapper;

    @Resource
    private CompanyMapper companyMapper;

    @Resource
    private UserMapper userMapper;

    public Result<?> saveReply(Reply reply) {
        replyMapper.insert(reply);
        return Result.success();
    }

    public Result<?> getReply(int demand_id,Page<Reply> page2) {
        // 创建查询条件
        LambdaQueryWrapper<Reply> wrapper = Wrappers.<Reply>lambdaQuery().eq(Reply::getDemandId, demand_id);

        // 执行分页查询
        IPage<Reply> replyPage = replyMapper.selectPage(page2, wrapper);

        // 创建 DTO 列表
        List<ReplyDTO> replyDTOs = new ArrayList<>();
        for (Reply reply : replyPage.getRecords()) {
            // 获取对应的用户信息
            User user = userMapper.selectById(reply.getUserId());
            ReplyDTO replyDTO = new ReplyDTO(
                    reply.getReply(),
                    reply.getDate(),
                    user != null ? user.getUsername() : "Unknown"  // 处理可能的用户为 null 的情况
            );
            replyDTOs.add(replyDTO);
        }

        // 将 DTO 列表封装为分页对象
        Page<ReplyDTO> resultPage = new Page<>(replyPage.getCurrent(), replyPage.getSize(), replyPage.getTotal());
        resultPage.setRecords(replyDTOs);

        // 返回分页结果
        return Result.success(resultPage);
    }
}

