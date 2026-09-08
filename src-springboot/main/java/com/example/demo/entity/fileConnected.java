package com.example.demo.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@TableName("fileConnected")
@Data
public class fileConnected {
    @TableId(type = IdType.AUTO)
    private Integer id;
    private String filename;
    private Double filesize;
    private String username;
    private String demandname;
    private String filepath;
    private Integer fileid;
    private String pass;
}
