package com.example.demo.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import lombok.Data;

@TableName("requirement")
@Data
public class Requirement {
    @TableId(type = IdType.AUTO)
    private Integer id;
    private String title;
    private String star;
    private String state;
    private String date;
    private String content;
    private Integer userId;

}
