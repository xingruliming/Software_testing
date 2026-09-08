package com.example.demo.controller;

import com.example.demo.commom.Result;
import com.example.demo.entity.Requirement;
import com.example.demo.entity.RequirementDTO;
import com.example.demo.service.CompanyService;
import jakarta.annotation.Resource;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/company")
public class CompanyController {

    @Resource
    private CompanyService companyService;

    @PostMapping("publish")
    public Result<?> addRequirement(@RequestBody Requirement requirement){

        return companyService.saveRequirement(requirement);
    }

    @GetMapping("requirement")//已发布的
    public Result<?> getRequirements(@RequestParam String state,@RequestParam int userId){
        return companyService.pRequirement(state,userId);
    }

    @GetMapping("requirement/detail")//展示更改前的
    public Result<?> updateRequirements(@RequestParam int id){
        return companyService.Requirement(id);
    }

    @PostMapping("requirement/detail")//更新需求
    public Result<?> updateRequirements(@RequestBody Requirement requirement){
        return companyService.updateRequirement(requirement);
    }

    @DeleteMapping("requirement/detail/{id}")
    public Result<?> deleteRequirement(@PathVariable int id){
        return companyService.deleteDemand(id);
    }

    @GetMapping("reply")
    public Result<?> getTDU(@RequestParam String state,
                            @RequestParam(required = false) String star,
                            @RequestParam Integer id){
        return companyService.getTDU(state,star,id);
    }

    @PutMapping("reply")
    public Result<?> updateTDU(@RequestBody RequirementDTO requirementDTO){
        return companyService.star(requirementDTO);
    }
}
