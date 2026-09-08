package com.example.demo.service;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.example.demo.commom.Result;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.demo.entity.Announcement;
import com.example.demo.mapper.AnnouncementMapper;
import jakarta.annotation.Resource;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

@Service
public class AnnouncementService {

    @Resource
    private AnnouncementMapper announcementMapper;

    public Page<Announcement> findAnnouncements(Integer pageNum, Integer pageSize,String state) {
        Page<Announcement> page = new Page<>(pageNum, pageSize);
        // 不使用查询条件，获取所有公告
        QueryWrapper<Announcement> queryWrapper = new QueryWrapper<>();

        if (state != null && !state.isEmpty()) {
            queryWrapper.eq("state", state); // 假设数据库中状态字段名为 "state"
        }

        // 使用查询条件获取公告
        return announcementMapper.selectPage(page, queryWrapper);
    }

    public Page<Announcement> findSpecificAnnouncements(Integer pageNum, Integer pageSize,String state,String title,String time) {
        Page<Announcement> page = new Page<>(pageNum, pageSize);
        // 不使用查询条件，获取所有公告
        QueryWrapper<Announcement> queryWrapper = new QueryWrapper<>();

        if (state != null && !state.isEmpty()) {
            queryWrapper.eq("state", state); // 假设数据库中状态字段名为 "state"
        }

        // 根据标题关键字过滤，使用模糊查询
        if (title != null && !title.trim().isEmpty()) {
            queryWrapper.like("title", title.trim()); // 假设数据库中标题字段名为 "title"

        }

        // 按日期过滤，将数据库中的时间字段格式化为 YYYY-MM-DD 进行匹配
        if (time != null && !time.trim().isEmpty()) {
            queryWrapper.apply("DATE_FORMAT(time, '%Y-%m-%d') = {0}", time.trim());

        }
        // 使用查询条件获取公告
        return announcementMapper.selectPage(page, queryWrapper);
    }

    public void createAnnouncement(Announcement announcement) {
        announcementMapper.insert(announcement);
    }

    public void deleteAnnouncement(List<Integer> ids) {

        for (Integer item : ids) {
            announcementMapper.deleteById(item);
        }

    }

    public Result<?> findSelected(List<Integer> ids) {

        for (Integer item : ids) {
            Announcement announcement = announcementMapper.selectById(item);

            if(announcement!=null && Objects.equals(announcement.getState(), "已发布")){
                return Result.error("-1","存在已发布的公告");
            }
        }

        for(Integer item : ids){
            Announcement announcement = announcementMapper.selectById(item);
            if(announcement != null && Objects.equals(announcement.getState(), "未发布")) {
                // 更新状态
                announcement.setState("已发布");
                DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
                announcement.setTime(LocalDateTime.now().format(formatter));
                // 将更改保存到数据库
                announcementMapper.updateById(announcement);
            }
        }
        return Result.success();
    }


}
