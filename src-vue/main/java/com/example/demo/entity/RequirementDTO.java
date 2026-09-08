package com.example.demo.entity;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@TableName("requirement_dto")
@Data
public class RequirementDTO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String title;
    private String date;
    private Integer userId;
    private String state;
    private String content;
    private String star;
    private Integer demandId;
    private String publisher;
    // 默认构造函数
    public RequirementDTO() {
    }

    // 带参数的构造函数
    public RequirementDTO(String title, String date, Integer userId , String state , String content , String star, Integer demandId , String publisher) {
        this.title = title;
        this.date = date;
        this.userId = userId;
        this.state = state;
        this.content = content;
        this.star = star;
        this.demandId = demandId;
        this.publisher = publisher;
    }

}
