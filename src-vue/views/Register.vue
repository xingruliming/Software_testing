<template>
  <div class="login-container">
    <div class="welcome-title">欢迎注册</div>
    <el-form :model="form" :rules="rules" label-width="100px" size="default" class="register-form">
      <el-form-item label="用户名" prop="username">
        <el-input v-model="form.username" :prefix-icon="User" />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input v-model="form.password" :prefix-icon="Lock" show-password />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirm">
        <el-input v-model="form.confirm" :prefix-icon="Lock" show-password />
      </el-form-item>
      <el-form-item>
        <el-radio-group v-model="form.identity">
          <el-radio value="用户">用户</el-radio>
          <el-radio value="企业">企业</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item>
        <el-button style="width: 250px" type="primary" @click="register">注册</el-button>
      </el-form-item>
      <el-form-item>
        <el-button style="width: 250px" type="primary" @click="back">返回</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script>
import {request} from "@/utils/request";

export default {
  name: "Register",
  computed: {
    User() {
      return User
    },
    Lock(){
      return Lock
    }
  },
  data(){
    return {
      form: {},
      rules:{
        username:[
          {required:true,message:'请输入用户名',trigger:'blur'}
        ],
        password:[
          {required:true,message:'请输入密码',trigger:'blur',}
        ],
        confirm: [
          { required: true, message: '请确认密码', trigger: 'blur' },
        ]

      }
    }
  },
  methods:{
    register(){

  console.log(this.form)

      if(!this.form.username){
        this.$message.error('请输入用户名！');
        return
      }

      if(this.form.password !== this.form.confirm){
        this.$message.error('两次密码输入不一致');
        return
      }

      if(this.form.password.length <= 3 ){
        this.$message.error('密码长度至少在三位以上');
        return
      }

      request.post("/register",this.form).then(res =>{
        if(res.code === '0'){
          this.$message.success('注册成功！'); // 成功反馈
          this.$router.push("/login")  //跳转登录
        }
        else{
          this.$message.error(res.msg);
        }
      })
    },
    back(){
      this.$router.push("/login");
    }
  }
}
import '@/assets/css/global.css'
import {User} from '@element-plus/icons-vue'
import {Lock} from '@element-plus/icons-vue'
</script>