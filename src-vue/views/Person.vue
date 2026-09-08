<template>
  <div class="card-container">
    <div class="card-header">
      <div class="info-label">{{ profileLabel }}</div>
    </div>
    <el-card style="width: 100%; position: relative;">
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="username" disabled></el-input>
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickName" ></el-input>
        </el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="form.sex">
            <el-radio value="男" size="large">男</el-radio>
            <el-radio value="女" size="large">女</el-radio>
            <el-radio value="未知" size="large">未知</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="年龄">
          <el-input v-model="form.age" ></el-input>
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.address" ></el-input>
        </el-form-item>
        <el-form-item >
          <el-radio-group v-model="identity" disabled>
            <el-radio value="用户">用户</el-radio>
            <el-radio value="企业">企业</el-radio>
            <el-radio value="管理员">管理员</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" ></el-input>
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-model="form.phoneNumber" ></el-input>
        </el-form-item>
        <el-form-item label="密码" class="inline-form">
          <el-input v-model="form.password" type="password" disabled></el-input>
          <el-button type="danger" @click="showPasswordDialog">修改密码</el-button>
        </el-form-item>
      </el-form>
      <div style="text-align: center">
        <el-popconfirm title="确认保存吗?" @confirm="update()">
          <template #reference>
            <el-button type="primary" >保存</el-button>
          </template>
        </el-popconfirm>
      </div>

    </el-card>
  </div>

  <!-- 弹出对话框 -->
  <el-dialog title="修改密码" v-model="dialogVisible">
    <el-form :model="passwordForm" ref="passwordForm" :rules="rules">
      <el-form-item label="原密码" prop="oldPassword" >
        <el-input v-model="passwordForm.oldPassword" type="password" show-password></el-input>
      </el-form-item>
      <el-form-item label="新密码" prop="newPassword">
        <el-input v-model="passwordForm.newPassword" type="password" show-password></el-input>
      </el-form-item>
    </el-form>
    <div slot="footer" class="dialog-footer">
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="submitPasswordForm">确认修改</el-button>
    </div>
  </el-dialog>

</template>


<script>
import { mapGetters, mapActions } from 'vuex';
import '@/assets/css/global.css'
import {request} from "@/utils/request";
export default {
  name: "Person",
  data(){
    return{
      form:{},
      dialogVisible: false,
      passwordForm: {
        oldPassword: '',
        newPassword: ''
      },
      rules: {
        oldPassword: [
          { required: true, message: '请输入原密码', trigger: 'blur' },
        ],
        newPassword: [
          { required: true, message: '请输入新密码', trigger: 'blur' },
        ]
      },
    }
  },

  computed: {
    ...mapGetters(['getUsername','getIdentity']),  // 获取用户名的 getter
    username() {
      return this.getUsername; // 绑定到表单中
    },
    identity() {
      return this.getIdentity;
    },
    profileLabel() {
      // 根据身份类型动态显示“个人资料”或“企业资料”
      return this.identity === '用户' ? '个人资料' : '企业资料';
    }
  },
  created(){
    request.get("/home/user/person", { params: { username: this.getUsername } }).then(res =>{
      console.log(res)
      this.form=res.data

    })
  },
  methods:{

    submitPasswordForm() {
      if(!this.passwordForm.oldPassword ){
        this.$message.error('请输入原密码！')
        return
      }
      else if(!this.passwordForm.newPassword ){
        this.$message.error('请输入新密码！')
        return
      }
      else if (this.passwordForm.oldPassword !== this.form.password) {
        this.$message.error('原密码不正确');
        return;
      }
      else if(this.passwordForm.newPassword.length <= 3){
        this.$message.error('新密码长度至少大于三位');
        return;
      }
      else if (this.passwordForm.newPassword === this.passwordForm.oldPassword) {
        this.$message.error('新密码不能与原密码相同');
        return;
      }

      const requestData = {
        id: this.form.id,
        password: this.passwordForm.newPassword
      };
      request.put('/client/person' , requestData).then(res =>{
        if(res.code === '0'){
          console.log(res.data)
          this.$message.success('修改成功'); // 成功反馈
          this.dialogVisible = false; // 隐藏对话框
          this.form.password = this.passwordForm.newPassword
          this.passwordForm.oldPassword = ''
          this.passwordForm.newPassword = ''

        }
        else{
          this.$message.error('修改错误');
        }
      })
    },
    update(){
      request.put("/home/user/person",this.form).then(res => {
        console.log(res)
        if(res.code === '0'){
          this.$message.success('保存成功！'); // 成功反馈
        }
        else{
          this.$message.error('保存失败');
        }


      })

    },
    showPasswordDialog() {
      this.dialogVisible = true;
      this.passwordForm={};
    },
  },

}


</script>

<style scoped>

</style>