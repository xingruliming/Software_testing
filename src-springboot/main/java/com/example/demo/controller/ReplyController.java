package com.example.demo.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.demo.commom.Result;
import com.example.demo.entity.Reply;
import com.example.demo.entity.ReplyDTO;
import com.example.demo.entity.User;
import com.example.demo.service.ReplyService;
import jakarta.annotation.Resource;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping
public class ReplyController {
    @Resource
    private ReplyService replyService;

    @PostMapping("/company/requirement")
    public Result<?> SaveReply(@RequestBody Reply reply) {
        return replyService.saveReply(reply);
    }

    @GetMapping("/company/requirement/reply")
    public Result<?> GetAllReply(@RequestParam int demandId,
                                 @RequestParam(defaultValue = "1") Integer pageNum,
                                 @RequestParam(defaultValue = "10") Integer pageSize) {
        // 创建分页对象
        Page<Reply> page = new Page<>(pageNum, pageSize);
        // 调用 replyService 获取分页的回复数据
        return replyService.getReply(demandId, page);
    }
}
