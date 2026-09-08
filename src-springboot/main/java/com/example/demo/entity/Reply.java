package com.example.demo.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import lombok.Data;

@TableName("reply")
@Data
public class Reply {
    @TableId(type = IdType.AUTO)
    private Integer id;
    private String reply;
    private String date;
    private int userId;
    private int demandId;
}
