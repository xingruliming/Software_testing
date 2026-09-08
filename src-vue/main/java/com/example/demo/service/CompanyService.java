package com.example.demo.service;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.example.demo.commom.Result;
import com.example.demo.entity.Requirement;
import com.example.demo.entity.RequirementDTO;
import com.example.demo.entity.User;
import com.example.demo.mapper.CompanyMapper;
import com.example.demo.mapper.RequirementDTOMapper;
import com.example.demo.mapper.UserMapper;
import jakarta.annotation.Resource;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.RestController;

import java.util.*;

@Service
public class CompanyService {
    @Resource
    private CompanyMapper companyMapper;

    @Resource
    private UserMapper userMapper;

    @Resource
    private RequirementDTOMapper requirementDTOMapper;

    public Result<?> saveRequirement(Requirement requirement){
        // 根据 title 查询是否已存在记录
        Requirement existingRequirement = companyMapper.selectOne(Wrappers.<Requirement>lambdaQuery().eq(Requirement::getTitle, requirement.getTitle()));
        if (existingRequirement != null) {
            // 如果找到相同的 title，返回错误消息
            return Result.error("-1","标题重复！");
        }
        else{
            companyMapper.insert(requirement);
            return Result.success();
        }
    }

    public Result<?> pRequirement(String state, int userId) {

        // 使用 selectList 查询符合 state 和 userId 的记录
        List<Requirement> existingRequirements = companyMapper.selectList(
                Wrappers.<Requirement>lambdaQuery()
                        .eq(Requirement::getState, state)
                        .eq(Requirement::getUserId, userId) // 根据 userId 过滤
        );

        if (!existingRequirements.isEmpty()) {
            // 返回查询到的所有需求
            return Result.success(existingRequirements);
        } else {
            if(Objects.equals(state, "已发布")) {// 如果没有找到符合条件的需求，返回错误消息
                return Result.error("-1", "不存在发布的需求");
            }
            else{
                return Result.error("-2","不存在保存的需求");
            }
        }
    }

    public Result<?> Requirement(int id){
        Requirement existingRequirement = companyMapper.selectOne(Wrappers.<Requirement>lambdaQuery().eq(Requirement::getId, id));
        if (existingRequirement != null) {
            return Result.success(existingRequirement);
        }
        else{
            return Result.error("-1", "不存在该需求");
        }
    }

    public Result<?> updateRequirement(Requirement requirement){
        Requirement existingRequirement = companyMapper.selectById(requirement.getId());
        if (existingRequirement != null) {
            companyMapper.updateById(requirement);
            return Result.success(requirement);
        }
        else{
            System.out.println("1");
            return Result.error("-1","更新失败");

        }
    }

    public Result<?> deleteDemand(int id){
        Requirement existingRequirement = companyMapper.selectById(id);
        if (existingRequirement != null) {
            companyMapper.deleteById(id);
            return Result.success();
        }
        else{
            return Result.error("-1","删除失败");
        }
    }

    public Result<?> published_Requirement(String state){
        List<Requirement> existingRequirements = companyMapper.selectList(
                Wrappers.<Requirement>lambdaQuery().eq(Requirement::getState, state));

        if (!existingRequirements.isEmpty()) {
            // 返回查询到的所有需求
            return Result.success(existingRequirements);
        } else {
            // 如果没有找到符合条件的需求，返回错误消息
            return Result.error("-1", "不存在发布的需求");
        }
    }

    public Result<?> getTDU(String state, String star, Integer id) {
        User user1 = userMapper.selectById(id);  // 当前用户
        List<RequirementDTO> requirementDTOs = new ArrayList<>();
        List<Requirement> requirements = new ArrayList<>();

        // 查询需求数据
        if (Objects.equals(star, "true")) {
            requirements = companyMapper.selectList(
                    Wrappers.<Requirement>lambdaQuery().eq(Requirement::getState, state).eq(Requirement::getStar, star));
        } else {
            requirements = companyMapper.selectList(
                    Wrappers.<Requirement>lambdaQuery().eq(Requirement::getState, state));
        }

        // 遍历需求数据
        for (Requirement requirement : requirements) {
            User user2 = userMapper.selectById(requirement.getUserId());  // 需求发布者

            // 处理非收藏需求
            if (!Objects.equals(star, "true")) {
                RequirementDTO requirementDTO = new RequirementDTO(
                        requirement.getTitle(),
                        requirement.getDate(),
                        id,
                        requirement.getState(),
                        requirement.getContent(),
                        "false",
                        requirement.getId(),
                        user2.getUsername()
                );

                // 查询是否已有相同id用户的需求DTO
                List<RequirementDTO> existingDTOs = requirementDTOMapper.selectList(
                        Wrappers.<RequirementDTO>lambdaQuery().eq(RequirementDTO::getDemandId, requirementDTO.getDemandId())
                );
                // 检查是否重复
                boolean isDuplicate = false;
                for (RequirementDTO existingDTO : existingDTOs) {
                    if (existingDTO.getUserId() == id) {
                        // 如果标题和用户名都匹配，认为是重复
                        isDuplicate = true;
                        break;
                    }
                }

                if (!isDuplicate) {
                    // 如果没有重复的标题用户，插入到数据库
                    requirementDTOMapper.insert(requirementDTO);
                } else {
                    // 如果发现重复，可以执行一些处理
                    System.out.println("标题重复，无法插入！");
                }

                RequirementDTO existing = requirementDTOMapper.selectOne(
                        Wrappers.<RequirementDTO>lambdaQuery().eq(RequirementDTO::getDemandId, requirementDTO.getDemandId()).eq(RequirementDTO::getUserId,requirementDTO.getUserId())
                );
                requirementDTO.setId(existing.getId());
                requirementDTO.setStar(existing.getStar());
                requirementDTOs.add(requirementDTO);
            } else {
                // 处理收藏需求
                List<RequirementDTO> requirementDTOss = requirementDTOMapper.selectList(
                        Wrappers.<RequirementDTO>lambdaQuery().eq(RequirementDTO::getDemandId, requirement.getId())
                );
                for (RequirementDTO requirementDTO : requirementDTOss) {
                    if (Objects.equals(requirementDTO.getUserId(), id) && requirementDTO.getStar().equals("true")) {
                        System.out.println(requirementDTO);
                        requirementDTOs.add(requirementDTO);
                    }
                }
            }
        }

        return Result.success(requirementDTOs);
    }


    public Result<?> star(RequirementDTO requirementDTO){

        Requirement existingRequirement = companyMapper.selectById(requirementDTO.getDemandId());
        RequirementDTO existingRequirementDTO = requirementDTOMapper.selectOne(
                Wrappers.<RequirementDTO>lambdaQuery().eq(RequirementDTO::getDemandId, requirementDTO.getDemandId()).eq(RequirementDTO::getUserId, requirementDTO.getUserId()));
        if (existingRequirement != null) {
            existingRequirement.setStar(requirementDTO.getStar());
            companyMapper.updateById(existingRequirement);

            existingRequirementDTO.setStar(requirementDTO.getStar());
            requirementDTOMapper.updateById(existingRequirementDTO);
            System.out.println(existingRequirementDTO);

            return Result.success(existingRequirementDTO);
        }
        else{
            return Result.error("-1","star wrong");
        }
    }
}
