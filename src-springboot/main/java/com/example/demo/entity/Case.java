package com.example.demo.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@TableName("file")
@Data
public class Case {
    @TableId(type = IdType.AUTO)
    private Integer id;
    private String fileName;
    private String filePath;
    private String fileType;
    private Double fileSize;
    private Integer userId;
    private Integer demandId;
    private Integer companyId;

}
