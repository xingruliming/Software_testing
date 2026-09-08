package com.example.demo.controller;

import com.example.demo.commom.Result;
import com.example.demo.entity.Invite;
import com.example.demo.service.InviteService;
import jakarta.annotation.Resource;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping
public class InviteController {
    @Resource
    private InviteService inviteService;

    @PostMapping("/company/user/")
    public Result<?> inviteUser(@RequestBody Invite invite) {
        return inviteService.invite(invite);
    }

    @GetMapping("/home/{id}")
    public Result<?> getInvited(@PathVariable Integer id) {
        return inviteService.getAll(id);
    }

    @PutMapping("/home")
    public Result<?> selectOption(@RequestBody Invite invite) {

        return inviteService.select(invite);
    }
}
