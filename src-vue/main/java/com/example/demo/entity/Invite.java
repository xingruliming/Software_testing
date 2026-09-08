package com.example.demo.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@TableName("invite")
@Data
public class Invite {
    @TableId(type = IdType.AUTO)
    private Integer id;
    private Integer userId;
    private Integer companyId;
    private String state;
    private String companyName;
}
