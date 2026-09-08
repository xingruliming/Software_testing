<template>
  <div class="background">
<!--    功能区域-->
    <div style="margin: 10px 0">
      <el-button style="margin-left: 20px" type="primary" @click="add">新增</el-button>
<!--      <el-button style="margin-left: 20px" type="primary">导入</el-button>
      <el-button style="margin-left: 20px" type="primary">导出</el-button>-->
    </div>
    <!--      搜索区域-->
    <div style="margin-bottom: 10px">
      <el-input v-model="search" style="width: 240px ;margin-left: 20px" placeholder="请输入关键字" clearable/>
      <el-button type="primary" style="margin-left: 7px" @click="load"> 查询</el-button>
    </div>
      <el-table :data="tableData" stripe style="width: calc(100vw - 150px)" border>
        <el-table-column prop="username" label="用户名"  />
        <el-table-column prop="identity" label="身份"  />
        <el-table-column prop="nickName" label="昵称" />
        <el-table-column prop="age" label="年龄" />
        <el-table-column prop="sex" label="性别" />
        <el-table-column prop="address" label="地址" />

        <el-table-column fixed="right" label="操作" min-width="55">
          <template #default="scope">
            <el-button link type="primary"  @click="handleEdit(scope.row)">编辑</el-button>
            <el-popconfirm title="确认删除吗?" @confirm="handleDelete(scope.row.id)">
              <template #reference>
                <el-button type="text">删除</el-button>
              </template>

            </el-popconfirm>

          </template>
        </el-table-column>

      </el-table>
    <div  style="margin: 10px 0">
      <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[5,10,20]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
      />

      <el-dialog v-model="dialogVisible" title="提示" width="30%">
      <el-form :model="form"  ref="formRef" label-width="120px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" style="width: 80%"/>
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickName" style="width: 80%"/>
        </el-form-item>
        <el-form-item label="年龄">
          <el-input v-model="form.age"  style="width: 80%"/>
        </el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="form.sex">
            <el-radio value="男" size="large">男</el-radio>
            <el-radio value="女" size="large">女</el-radio>
            <el-radio value="未知" size="large">未知</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="地址">
          <el-input type="textarea" v-model="form.address" style="width: 80%"/>
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input  v-model="form.email" style="width: 80%"/>
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-model="form.phoneNumber" style="width: 80%"/>
        </el-form-item>
        <el-form-item label="密码">
          <el-input  v-model="form.password" style="width: 80%"/>
        </el-form-item>
      </el-form>
        <template #footer>
          <div class="dialog-footer">
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" @click="save">确定</el-button>
          </div>
        </template>
      </el-dialog>


    </div>
  </div>
</template>

<script>
import {request} from "@/utils/request";

export default {

  name: 'HomeView',
  components: {

  },
  data() {
    return {
      form: {},
      dialogVisible: false,
      search: '',
      currentPage: 1,
      pageSize: 10,
      total: 10,
      tableData: [],
    }
  },
  created(){
    this.load()
  },

  methods:{
    load(){
      request.get("/home/user",{
        params:{
          pageNum: this.currentPage,
          pageSize: this.pageSize,
          search: this.search
        }
      }).then(res =>{
        console.log(res)
        this.tableData=res.data.records
        this.total=res.data.total
      })
    },
    add(){
      this.dialogVisible=true
      this.form = {}
    },
    save() {
      // 在保存之前，先进行基本的验证
      if(this.form.id){//更新

        if (this.validateForm()) {
          request.put("/home/user", this.form).then(res => {
            console.log(res);
            if(res.code === '0'){
              this.$message.success('编辑成功！'); // 成功反馈
              this.dialogVisible = false; // 隐藏对话框
              this.load(); // 刷新数据表
            }
            else{
              this.$message.error('用户已存在！');
            }

          });
        }
      }else{
        if (this.validateForm()) {
          request.post("/home/user", this.form).then(res => {
            console.log(res);
            if(res.code === '0'){
              this.$message.success('添加成功！'); // 成功反馈
            }
            else{
              this.$message.error('用户已存在！');
            }
            this.dialogVisible = false; // 隐藏对话框
            this.load(); // 刷新数据表
          });
        }
      }

    },
    validateForm() {
      // 验证用户名
     if (!this.form.username) {
        this.$message.error('请输入用户名');
        return false;
      }
      if (this.form.username.length < 1 || this.form.username.length > 15) {
        this.$message.error('用户名长度应在 1 到 15 个字符之间');
        return false;
      }

      // 验证昵称
      if (!this.form.nickName && this.form.identity !== '企业') {
        this.$message.error('请输入昵称');
        return false;
      }

      // 验证年龄
      const age = this.form.age;
      if (!age && this.form.identity !== '企业') {
        this.$message.error('请输入年龄');
        return false;
      }
      if (isNaN(age)) {
        this.$message.error('年龄必须是一个数字');
        this.form.age = ''; // 清空输入框
        return false;
      }

      // 验证性别
      if (!this.form.sex) {
        this.$message.error('请选择性别');
        return false;
      }

      // 验证地址
      if (!this.form.address || this.form.address.length < 3) {
        this.$message.error('地址至少包含 3 个字符');
        return false;
      }

      if(!this.form.password){
        this.$message.error('密码必填！');
        return false;
      }

      if(this.form.password.length <= 3 ){
        this.$message.error('密码长度至少在三位以上');
        return false;
      }
      return true; // 如果所有验证都通过，返回 true
    },


    handleEdit(row){
      this.form = JSON.parse(JSON.stringify(row))//将 row（当前行的数据）深拷贝到组件的 form 对象中。
      this.dialogVisible=true;
    },
    handleDelete(id){
      console.log(id)
      request.delete("/home/user/" + id).then(res =>
      {
        if(res.code === '0'){
          this.$message.success('删除成功！'); // 成功反馈
        }
        else{
          this.$message.error('删除失败！');
        }
        this.load();
      })
    },
    handleCurrentChange(pageNum){ //改变当前页码触发
      this.currentPage=pageNum;
      this.load();
    },
    handleSizeChange(pageSize){ //改变当前每页的个数触发
      this.pageSize=pageSize;
      this.load();
    }
  }
}

</script>
