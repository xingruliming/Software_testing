package com.example.demo.entity;
import lombok.Data;
@Data
public class ReplyDTO {
    private String reply;
    private String date;
    private String username;

    public ReplyDTO(String reply, String date, String username) {
        this.reply = reply;
        this.date = date;
        this.username = username;
    }
}
